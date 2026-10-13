# Etiquetas Jonas

Aplicativo desktop em Python para etiquetas preenchidas de 60 × 40 mm na Elgin L42 Pro Full, via driver do Windows.

Inclui produto, datas com calendário, conservação, quantidade, prévia e cadastro persistente de responsáveis.

## Preparar o projeto após clonar

Ambiente usado no desenvolvimento: Windows 11 de 64 bits e Python 3.13.

No terminal, dentro da pasta do projeto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Instale também o driver da Elgin no Windows e configure **Térmica direta**, **Etiquetas com intervalos** e papel de **60 × 40 mm**. Consulte `LEIA-ME-PC-DO-X.txt` para os links e o passo a passo.

## Abrir

Clique duas vezes em **Iniciar.bat**, ou execute `main.py` no PyCharm usando o ambiente `.venv` deste projeto.

As dependências do aplicativo estão em `requirements.txt`.

## Executável para o PC do X

Na entrega local preparada, o pacote está em `entrega/EtiquetasJonas-PC-do-X.zip`. Esse ZIP e o EXE não são versionados neste repositório. Extraia a pasta completa em Documentos e abra `EtiquetasJonas.exe`. Não é necessário instalar Python no computador que executa o EXE. A pasta `dados` deve ficar junto dele para preservar os responsáveis.

Para gerar novamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\Gerar-exe.bat
```

O EXE será gerado em `entrega/EtiquetasJonas/EtiquetasJonas.exe`. Ao preparar uma entrega, copie o guia para essa pasta. Se desejar transferir os responsáveis existentes, copie também a pasta `dados` e compacte a pasta completa em ZIP. O instalador oficial do driver pode ser baixado pelo link do guia; ele não é redistribuído pelo Git.

Atualizações no PC do X devem substituir apenas o EXE, preservando a pasta `dados` existente.

Para verificar o executável sem imprimir nem alterar o cadastro real:

```powershell
.\entrega\EtiquetasJonas\EtiquetasJonas.exe --self-test
```

O resultado é salvo em `verificacao-exe.json`, ao lado do executável. Esse teste verifica interface, calendário, desenho e persistência de um cadastro temporário; a impressão física deve ser conferida separadamente.

## Primeiro teste

1. Preencha o produto. A manipulação começa no dia de hoje; clique na data ou em **Calendário** para escolher outro dia. A validade também possui calendário, navegação entre meses e botão **Hoje**.
2. Ao lado de **Responsável**, use **+** para cadastrar uma pessoa. Depois basta selecioná-la na lista. Para excluir, selecione a pessoa, clique em **X** e confirme.
3. Selecione refrigerado, congelado ou ambiente. A validade é informada por você; o aplicativo não calcula prazos de alimentos.
4. Confira a prévia e escolha a impressora Elgin L42.
5. Deixe a quantidade em **1** e clique em **Imprimir etiquetas**.
6. Confira tamanho, margens, acentos, legibilidade e avanço de uma etiqueta por página.

Para o rolo térmico direto, mantenha o driver configurado em **térmica direta**, com papel de **60 mm de largura por 40 mm de altura**. O aplicativo solicita esse tamanho por trabalho sem salvar configurações padrão. Se o driver retornar outro tamanho, interrompe a impressão.

## Recursos

- Prévia atualizada ao digitar, com o mesmo desenho utilizado na impressão.
- Quantidade entre 1 e 500, uma página por etiqueta.
- Validação de datas e campos obrigatórios.
- Fonte reduzida para nomes maiores; textos que não cabem devem ser abreviados.
- Exportação em PNG.
- Confirmação de envio à fila; o resultado físico depende da impressora.

O cadastro de responsáveis é salvo em `dados/responsaveis.json`, dentro do projeto, e permanece disponível após fechar o aplicativo. Inclua essa pasta nos backups ou ao transferir o app para outro computador. Os demais campos são reiniciados ao abrir; esta versão não salva histórico de etiquetas.

O Git ignora cadastros, registros de impressão, ambiente virtual, arquivos do PyCharm e arquivos gerados pelo build.
