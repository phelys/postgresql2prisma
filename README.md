# PostgreSQL to Prisma Schema Generator

Aplicação web Flask que conecta em bancos de dados PostgreSQL e gera automaticamente arquivos de schema Prisma a partir de tabelas existentes.

## Requisitos

- Python 3.x
- PostgreSQL (servidor de banco de dados para conectar)
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd postgresql2prisma
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Rodar

Execute o comando:
```bash
python main.py
```

A aplicação estará disponível em: **http://localhost:5000**

## Liberando a Porta 5000 no Firewall do Ubuntu

Se você precisar acessar a aplicação de outros dispositivos na rede, será necessário liberar a porta 5000 no firewall.

### Usando UFW (Uncomplicated Firewall)

1. Verifique o status do firewall:
```bash
sudo ufw status
```

2. Libere a porta 5000:
```bash
sudo ufw allow 5000/tcp
```

3. Verifique se a regra foi adicionada:
```bash
sudo ufw status numbered
```

4. (Opcional) Se o UFW estiver inativo, ative-o:
```bash
sudo ufw enable
```

### Removendo a regra do firewall (quando não precisar mais)

```bash
sudo ufw delete allow 5000/tcp
```

### Permitir apenas de um IP específico

Para maior segurança, você pode liberar a porta apenas para um IP específico:
```bash
sudo ufw allow from 192.168.1.100 to any port 5000
```

## Como Usar

1. Acesse http://localhost:5000 no navegador
2. Preencha as credenciais do banco de dados PostgreSQL:
   - Host
   - Port
   - Database
   - User
   - Password
3. Clique em "Connect"
4. Selecione as tabelas que deseja gerar o schema Prisma
5. Escolha o formato de saída:
   - **Single File**: Todos os models em um único arquivo `.prisma`
   - **Multiple Files**: Um arquivo para cada tabela (download em ZIP)
6. Clique em "Generate Prisma Schema"

## Funcionalidades

- ✅ Conexão com bancos PostgreSQL
- ✅ Listagem de schemas e tabelas
- ✅ Geração automática de models Prisma
- ✅ Detecção de chaves primárias
- ✅ Mapeamento de tipos PostgreSQL → Prisma
- ✅ Suporte a múltiplos schemas
- ✅ Detecção de valores padrão (auto-increment, timestamps)
- ✅ Persistência de configurações de conexão

## Mapeamento de Tipos

| PostgreSQL | Prisma |
|------------|--------|
| integer, int4, serial | Int |
| bigint, int8, bigserial | BigInt |
| real, float4 | Float |
| double precision, float8 | Float |
| numeric, decimal | Decimal |
| varchar, text, char, etc. | String |
| timestamp, date, time | DateTime |
| boolean, bool | Boolean |
| json, jsonb | Json |
| uuid | String |
| bytea | Bytes |

## Estrutura do Projeto

```
postgresql2prisma/
├── main.py              # Aplicação Flask completa
├── requirements.txt     # Dependências Python
├── db_config.json      # Configurações salvas (auto-gerado)
└── README.md           # Este arquivo
```

## Troubleshooting

### Erro de conexão com PostgreSQL
- Verifique se as credenciais estão corretas
- Confirme que o PostgreSQL está rodando
- Verifique se o firewall do servidor PostgreSQL permite conexões

### Porta 5000 já em uso
Altere a porta no final do arquivo `main.py` ou mate o processo que está usando a porta:
```bash
sudo lsof -ti:5000 | xargs kill -9
```

## Licença

[Adicione a licença do projeto aqui]
