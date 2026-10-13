"""Etiquetas preenchidas de 60 × 40 mm via driver do Windows."""
from datetime import date, datetime
from pathlib import Path
import os
import sys
import calendar
import json
import logging
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageWin
import win32con
import win32gui
import win32print
import win32ui

CONSERVACOES = ("Refrigerado", "Congelado", "Ambiente")
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RESPONSAVEIS_PATH = APP_DIR / 'dados' / 'responsaveis.json'
LOG_PATH = APP_DIR / 'logs' / 'impressao.log'
logger = logging.getLogger('etiquetas')


def setup_logging():
    if not logger.handlers:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(LOG_PATH, maxBytes=500_000, backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')


def load_responsaveis(path):
    if not path.exists():
        return []
    names = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError('O cadastro de responsáveis possui um formato inválido.')
    return sorted({n.strip().casefold(): n.strip() for n in names}.values(), key=str.casefold)


def save_responsaveis(path, names):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class CalendarPicker(tk.Toplevel):
    def __init__(self, parent, variable, title):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.variable = variable
        try:
            self.selected = datetime.strptime(variable.get(), '%d/%m/%Y').date()
        except ValueError:
            self.selected = date.today()
        self.year, self.month = self.selected.year, self.selected.month
        self.body = ttk.Frame(self, padding=16)
        self.body.pack()
        self.draw_month()
        self.bind('<Escape>', lambda event: self.destroy())
        self.update_idletasks()
        self.geometry(f'+{parent.winfo_rootx()+100}+{parent.winfo_rooty()+150}')
        self.grab_set()

    def move_month(self, step):
        absolute = self.year * 12 + self.month - 1 + step
        year, month = divmod(absolute, 12)
        if 1 <= year <= 9999:
            self.year, self.month = year, month + 1
            self.draw_month()

    def choose(self, chosen):
        self.variable.set(chosen.strftime('%d/%m/%Y'))
        self.destroy()

    def draw_month(self):
        for child in self.body.winfo_children():
            child.destroy()
        ttk.Button(self.body, text='‹', width=3, command=lambda: self.move_month(-1)).grid(row=0, column=0)
        ttk.Label(self.body, text=f'{MESES[self.month-1]} de {self.year}', anchor='center').grid(row=0, column=1, columnspan=5)
        ttk.Button(self.body, text='›', width=3, command=lambda: self.move_month(1)).grid(row=0, column=6)
        for column, day in enumerate(('D', 'S', 'T', 'Q', 'Q', 'S', 'S')):
            ttk.Label(self.body, text=day, anchor='center').grid(row=1, column=column, pady=10)
        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(self.year, self.month)
        for row, week in enumerate(weeks, start=2):
            for column, day in enumerate(week):
                if day:
                    chosen = date(self.year, self.month, day)
                    caption = f'[{day}]' if chosen == self.selected else str(day)
                    ttk.Button(self.body, text=caption, width=4,
                               command=lambda d=chosen: self.choose(d)).grid(row=row, column=column, padx=2, pady=2)
        ttk.Button(self.body, text='Hoje', command=lambda: self.choose(date.today())).grid(row=8, column=0, columnspan=3, sticky='ew', pady=(12, 0))
        ttk.Button(self.body, text='Cancelar', command=self.destroy).grid(row=8, column=4, columnspan=3, sticky='ew', pady=(12, 0))


def validate(data):
    if not data['produto'] or not data['responsavel']:
        raise ValueError('Preencha produto e responsável.')
    dates = []
    for key in ('manipulacao', 'validade'):
        try:
            parsed = datetime.strptime(data[key], '%d/%m/%Y').date()
        except ValueError:
            raise ValueError('Informe datas válidas no formato DD/MM/AAAA.') from None
        if parsed.strftime('%d/%m/%Y') != data[key]:
            raise ValueError('Use DD/MM/AAAA, como 13/10/2026.')
        dates.append(parsed)
    if dates[1] < dates[0]:
        raise ValueError('A validade não pode ser anterior à manipulação.')
    if data['conservacao'] not in CONSERVACOES:
        raise ValueError('Escolha uma opção de conservação.')
    try:
        count = int(data['quantidade'])
    except ValueError:
        raise ValueError('A quantidade precisa ser um número inteiro.') from None
    if not 1 <= count <= 500:
        raise ValueError('Escolha entre 1 e 500 etiquetas.')
    return count


def render_label(data):
    image = Image.new('RGB', (1200, 800), 'white')
    draw = ImageDraw.Draw(image)
    fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'

    def text(value, x, y, width=1110, size=49, minimum=35, bold=False):
        for n in range(size, minimum - 1, -1):
            font = ImageFont.truetype(str(fonts / ('arialbd.ttf' if bold else 'arial.ttf')), n)
            if draw.textlength(value, font=font) <= width:
                draw.text((x, y), value, font=font, fill='black')
                return
        raise ValueError('Texto muito longo. Abrevie: ' + value)

    title_font = ImageFont.truetype(str(fonts / 'arialbd.ttf'), 83)
    title = 'XIS DO JONAS'
    draw.text(((1200 - draw.textlength(title, font=title_font)) / 2, 43), title, font=title_font, fill='black')
    draw.line((45, 151, 1155, 151), fill='black', width=3)
    text('PRODUTO:', 45, 177, size=37)
    text(data['produto'], 45, 224, size=65, minimum=38, bold=True)
    text('MANIPULAÇÃO:', 45, 331, width=475, size=43)
    text(data['manipulacao'], 535, 323, width=610, size=58, bold=True)
    text('VALIDADE:', 45, 423, width=475, size=43)
    text(data['validade'], 535, 415, width=610, size=58, bold=True)
    for name, x in zip(CONSERVACOES, (45, 440, 838)):
        y = 548
        draw.rectangle((x, y, x+39, y+39), outline='black', width=3)
        if data['conservacao'] == name:
            draw.line((x+7, y+20, x+16, y+31, x+33, y+8), fill='black', width=6)
        text(name.upper(), x+52, y-1, width=335 if x < 800 else 260, size=36, minimum=33)
    text('RESPONSÁVEL:', 45, 638, size=37)
    text(data['responsavel'], 45, 683, size=53, bold=True)
    return image


def printer_names():
    return sorted(p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS))


def print_labels(printer, image, count):
    setup_logging()
    logger.info('Iniciando envio: impressora=%s quantidade=%s', printer, count)
    handle = win32print.OpenPrinter(printer)
    dc, started = None, False
    try:
        mode = win32print.GetPrinter(handle, 2)['pDevMode']
        if mode is None:
            raise RuntimeError('O driver não forneceu as configurações de papel.')
        mode.PaperSize, mode.PaperWidth, mode.PaperLength = 256, 600, 400
        mode.Orientation, mode.Copies = win32con.DMORIENT_PORTRAIT, 1
        mode.Fields |= (win32con.DM_PAPERSIZE | win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH | win32con.DM_ORIENTATION | win32con.DM_COPIES)
        result = win32print.DocumentProperties(0, handle, printer, mode, mode, win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
        if result < 0:
            raise RuntimeError('O driver rejeitou o tamanho da etiqueta.')
        dc = win32ui.CreateDCFromHandle(win32gui.CreateDC('WINSPOOL', printer, mode))
        w, h = dc.GetDeviceCaps(110), dc.GetDeviceCaps(111)
        mm_w, mm_h = w * 25.4 / dc.GetDeviceCaps(88), h * 25.4 / dc.GetDeviceCaps(90)
        logger.info('Papel retornado pelo driver: %.2f x %.2f mm', mm_w, mm_h)
        if abs(mm_w-60) > 1 or abs(mm_h-40) > 1:
            raise RuntimeError(f'O driver retornou {mm_w:.1f} × {mm_h:.1f} mm. Configure papel 60 × 40 mm nas preferências e tente novamente.')
        ox, oy = dc.GetDeviceCaps(112), dc.GetDeviceCaps(113)
        dib = ImageWin.Dib(image)
        document = 'Etiquetas XIS DO JONAS ' + datetime.now().strftime('%H%M%S%f')
        dc.StartDoc(document)
        started = True
        job_id = None
        try:
            job_id = next((job['JobId'] for job in win32print.EnumJobs(handle, 0, 1000, 1)
                           if job['pDocument'] == document), None)
        except Exception:
            logger.warning('Não foi possível consultar o identificador do trabalho', exc_info=True)
        logger.info('StartDoc: documento=%s trabalho=%s', document, job_id)
        for page in range(count):
            dc.StartPage()
            dib.draw(dc.GetHandleOutput(), (-ox, -oy, w-ox, h-oy))
            dc.EndPage()
            logger.info('Página %s concluída', page + 1)
        dc.EndDoc()
        started = False
        logger.info('EndDoc concluído: trabalho=%s', job_id)
        return job_id
    except Exception:
        logger.exception('Falha durante o envio à impressora')
        if started:
            dc.AbortDoc()
        raise
    finally:
        if dc is not None:
            dc.DeleteDC()
        win32print.ClosePrinter(handle)


class App(tk.Tk):
    def __init__(self, responsaveis_path=RESPONSAVEIS_PATH):
        super().__init__()
        setup_logging()
        logger.info('Aplicativo aberto')
        self.responsaveis_path = responsaveis_path
        self.cadastro_error = None
        try:
            self.responsaveis = load_responsaveis(responsaveis_path)
        except (OSError, ValueError) as exc:
            self.responsaveis = []
            self.cadastro_error = str(exc)
        self.title('Etiquetas Jonas · 60 × 40 mm')
        self.geometry('1120x780')
        self.minsize(1000, 660)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TLabel', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 11), padding=9)
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)
        ttk.Label(outer, text='Etiquetas Jonas', font=('Segoe UI', 22, 'bold')).grid(row=0, column=0, sticky='w')
        ttk.Label(outer, text='Preencha os dados e confira a prévia antes de imprimir.').grid(row=1, column=0, sticky='w', pady=(5, 20))
        body = ttk.Frame(outer)
        body.grid(row=2, column=0, sticky='nsew')
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        form = ttk.Frame(body)
        form.grid(row=0, column=0, sticky='ns', padx=(0, 28))
        today = date.today().strftime('%d/%m/%Y')
        self.values = {key: tk.StringVar(value=value) for key, value in dict(produto='', manipulacao=today, validade=today, conservacao='Refrigerado', responsavel='', quantidade='1').items()}
        ttk.Label(form, text='Produto').pack(anchor='w', pady=(8, 4))
        ttk.Entry(form, textvariable=self.values['produto'], width=32, font=('Segoe UI', 12)).pack(fill='x')
        for key, label in [('manipulacao', 'Data de manipulação'), ('validade', 'Data de validade')]:
            ttk.Label(form, text=label).pack(anchor='w', pady=(8, 4))
            row = ttk.Frame(form)
            row.pack(fill='x')
            field = ttk.Entry(row, textvariable=self.values[key], width=15, state='readonly', cursor='hand2', font=('Segoe UI', 12))
            field.pack(side='left', fill='x', expand=True)
            field.bind('<Button-1>', lambda event, k=key, title=label: self.open_calendar(k, title))
            field.bind('<Return>', lambda event, k=key, title=label: self.open_calendar(k, title))
            ttk.Button(row, text='Calendário', command=lambda k=key, title=label: self.open_calendar(k, title)).pack(side='left', padx=(5, 0))
        ttk.Label(form, text='Responsável').pack(anchor='w', pady=(8, 4))
        row = ttk.Frame(form)
        row.pack(fill='x')
        self.responsavel_box = ttk.Combobox(row, textvariable=self.values['responsavel'], values=self.responsaveis, state='readonly', width=20, font=('Segoe UI', 12))
        self.responsavel_box.pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='+', width=2, command=self.add_responsavel).pack(side='left', padx=(5, 0))
        ttk.Button(row, text='X', width=2, command=self.remove_responsavel).pack(side='left', padx=(3, 0))
        ttk.Label(form, text='Conservação').pack(anchor='w', pady=(12, 4))
        ttk.Combobox(form, textvariable=self.values['conservacao'], values=CONSERVACOES, state='readonly', font=('Segoe UI', 12)).pack(fill='x')
        ttk.Label(form, text='Quantidade de etiquetas').pack(anchor='w', pady=(12, 4))
        ttk.Spinbox(form, from_=1, to=500, textvariable=self.values['quantidade'], width=10, font=('Segoe UI', 12)).pack(anchor='w')
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text='Prévia · 60 × 40 mm').grid(row=0, column=0, sticky='w', pady=(8, 12))
        self.preview_frame = ttk.Frame(right, width=570, height=380)
        self.preview_frame.grid(row=1, column=0, sticky='nsew')
        self.preview_frame.pack_propagate(False)
        self.preview = ttk.Label(self.preview_frame)
        self.preview.pack(expand=True)
        self.preview_frame.bind('<Configure>', lambda event: self.update_preview())
        ttk.Label(right, text='Impressora').grid(row=2, column=0, sticky='w', pady=(18, 4))
        self.printer = tk.StringVar()
        self.printer_box = ttk.Combobox(right, textvariable=self.printer, state='readonly', width=45)
        self.printer_box.grid(row=3, column=0, sticky='ew')
        ttk.Button(right, text='Atualizar impressoras', command=self.refresh_printers).grid(row=4, column=0, sticky='w', pady=5)
        actions = ttk.Frame(right)
        actions.grid(row=5, column=0, sticky='ew', pady=10)
        ttk.Button(actions, text='Salvar prévia PNG', command=self.save_preview).pack(side='left')
        self.print_button = ttk.Button(actions, text='Imprimir etiquetas', command=self.do_print)
        self.print_button.pack(side='right')
        self.status = tk.StringVar(value='Para o primeiro teste, use quantidade 1.')
        ttk.Label(outer, textvariable=self.status, wraplength=900).grid(row=3, column=0, sticky='w', pady=(16, 0))
        for var in self.values.values():
            var.trace_add('write', lambda *_: self.update_preview())
        self.update_preview()
        self.refresh_printers()
        if self.cadastro_error:
            self.after_idle(lambda: messagebox.showerror('Cadastro de responsáveis',
                f'Não foi possível ler {self.responsaveis_path}.\n{self.cadastro_error}\nO arquivo foi preservado. Corrija-o antes de alterar o cadastro.'))

    def open_calendar(self, key, title):
        CalendarPicker(self, self.values[key], title)

    def report_callback_exception(self, exc_type, exc_value, traceback):
        logger.error('Erro em botão/evento da tela', exc_info=(exc_type, exc_value, traceback))
        messagebox.showerror('Erro no aplicativo', f'{exc_value}\n\nRegistro: {LOG_PATH}', parent=self)

    def add_responsavel(self):
        if self.cadastro_error:
            messagebox.showerror('Cadastro indisponível', self.cadastro_error)
            return
        name = simpledialog.askstring('Adicionar responsável', 'Nome do responsável:', parent=self)
        if name is None:
            return
        name = ' '.join(name.split())
        if not name:
            messagebox.showerror('Nome obrigatório', 'Informe o nome da pessoa.')
            return
        existing = next((n for n in self.responsaveis if n.casefold() == name.casefold()), None)
        if existing:
            self.values['responsavel'].set(existing)
            return
        try:
            render_label(dict(self.data(), responsavel=name))
            names = sorted(self.responsaveis + [name], key=str.casefold)
            save_responsaveis(self.responsaveis_path, names)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Não foi possível adicionar', str(exc))
            return
        self.responsaveis = names
        self.responsavel_box['values'] = names
        self.values['responsavel'].set(name)
        self.status.set(f'{name} adicionado ao cadastro.')

    def remove_responsavel(self):
        if self.cadastro_error:
            messagebox.showerror('Cadastro indisponível', self.cadastro_error)
            return
        name = self.values['responsavel'].get()
        if name not in self.responsaveis:
            messagebox.showinfo('Selecione uma pessoa', 'Escolha o responsável que deseja remover.')
            return
        if not messagebox.askyesno('Remover responsável', f'Remover {name} da lista?', parent=self):
            return
        names = [n for n in self.responsaveis if n != name]
        try:
            save_responsaveis(self.responsaveis_path, names)
        except OSError as exc:
            messagebox.showerror('Não foi possível remover', str(exc))
            return
        self.responsaveis = names
        self.responsavel_box['values'] = names
        self.values['responsavel'].set('')
        self.status.set(f'{name} removido do cadastro.')

    def data(self):
        return {key: var.get().strip() for key, var in self.values.items()}

    def update_preview(self):
        try:
            data = self.data()
            data['produto'] = data['produto'] or 'Nome do produto'
            data['responsavel'] = data['responsavel'] or 'Nome do responsável'
            available_w = max(1, self.preview_frame.winfo_width())
            available_h = max(1, self.preview_frame.winfo_height())
            width = max(1, min(570, available_w, int(available_h * 1.5)))
            picture = render_label(data).resize((width, max(1, round(width / 1.5))), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(picture)
            self.preview.configure(image=self.preview_photo, text='')
        except Exception as exc:
            self.preview.configure(image='', text='Abrevie o texto para visualizar.')
            self.status.set(str(exc))

    def refresh_printers(self):
        try:
            names = printer_names()
            self.printer_box['values'] = names
            if self.printer.get() not in names:
                self.printer.set(next((n for n in names if 'L42' in n.upper()), ''))
            if not names:
                self.status.set('Nenhuma impressora encontrada. Instale o driver e atualize a lista.')
        except Exception as exc:
            self.status.set('Não foi possível listar impressoras: ' + str(exc))

    def save_preview(self):
        try:
            data = self.data()
            validate(data)
            picture = render_label(data)
            path = filedialog.asksaveasfilename(defaultextension='.png', initialfile='etiqueta-jonas.png', filetypes=[('Imagem PNG', '*.png')])
            if path:
                picture.save(path, dpi=(508, 508))
                self.status.set('Prévia salva em ' + path)
        except Exception as exc:
            messagebox.showerror('Confira os campos', str(exc))

    def do_print(self):
        logger.info('Botão Imprimir acionado')
        try:
            data = self.data()
            count = validate(data)
            picture = render_label(data)
            printer = self.printer.get()
            if not printer or 'L42' not in printer.upper():
                raise ValueError('Selecione a impressora Elgin L42.')
            self.print_button.configure(state='disabled')
            self.status.set('Enviando etiquetas para a fila de impressão…')
            self.update_idletasks()
            job_id = print_labels(printer, picture, count)
            receipt = f'\nTrabalho: {job_id}' if job_id is not None else ''
            self.status.set(f'{count} etiqueta(s) enviada(s) para {printer}.' + receipt.replace('\n', ' '))
            messagebox.showinfo('Enviado à impressora',
                f'{count} etiqueta(s) enviada(s) para {printer}.{receipt}\n\nConfira se a etiqueta saiu na impressora.', parent=self)
        except Exception as exc:
            logger.exception('Impressão não concluída')
            self.status.set('Impressão não concluída. Confira a mensagem de erro.')
            messagebox.showerror('Não foi possível imprimir', f'{exc}\n\nRegistro: {LOG_PATH}', parent=self)
        finally:
            self.print_button.configure(state='normal')


def self_test():
    """Verifica o executável sem imprimir nem alterar o cadastro real."""
    from tempfile import TemporaryDirectory
    report = {'frozen': bool(getattr(sys, 'frozen', False)), 'app_dir': str(APP_DIR)}
    app = None
    try:
        with TemporaryDirectory(dir=APP_DIR) as folder:
            path = Path(folder) / 'responsaveis.json'
            save_responsaveis(path, ['Pessoa de teste'])
            assert load_responsaveis(path) == ['Pessoa de teste']
            app = App(path)
            app.withdraw()
            app.update()
            today = date.today().strftime('%d/%m/%Y')
            sample = dict(produto='TESTE', manipulacao=today, validade=today,
                          conservacao='Ambiente', responsavel='Pessoa de teste', quantidade='2')
            assert validate(sample) == 2
            assert render_label(sample).size == (1200, 800)
            assert app.values['manipulacao'].get() == today
            assert list(app.responsavel_box['values']) == ['Pessoa de teste']
            popup = CalendarPicker(app, app.values['validade'], 'Teste calendário')
            popup.choose(date(2028, 2, 29))
            assert app.values['validade'].get() == '29/02/2028'
            report['printers'] = printer_names()
            app.destroy()
            app = None
        report['ok'] = True
        report['physical_print_tested'] = False
    except Exception as exc:
        report.update(ok=False, error=repr(exc))
    finally:
        if app is not None:
            app.destroy()
        (APP_DIR / 'verificacao-exe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        raise SystemExit(self_test())
    try:
        App().mainloop()
    except Exception as exc:
        messagebox.showerror('Não foi possível abrir o aplicativo',
            f'{exc}\n\nExtraia o aplicativo para uma pasta sua em Documentos, onde seja possível salvar o cadastro e os registros.')
