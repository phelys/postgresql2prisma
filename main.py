from flask import Flask, render_template_string, request, jsonify, send_file
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
import psycopg2.pool
import io
import zipfile
import json
import os
from datetime import datetime
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)
CORS(app)  # Adiciona suporte CORS

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Pool de conexões (mais robusto que conexão simples)
connection_pool = None

# Arquivo para persistir configurações
CONFIG_FILE = 'db_config.json'

# Cliente Grok (xAI) para integração com IA
grok_client = None
try:
    api_key = os.getenv('XAI_API_KEY')
    if api_key:
        grok_client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        logger.info("Cliente Grok (xAI) inicializado com sucesso")
    else:
        logger.warning("XAI_API_KEY não encontrada. Recurso de dicionário de dados desabilitado.")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Grok: {e}")

def load_config():
    """Carrega configurações salvas do arquivo JSON"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'postgres',
        'user': 'postgres',
        'password': ''
    }

def save_config(config):
    """Salva configurações no arquivo JSON"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {e}")
        return False

def get_db_connection():
    """Obtém uma conexão do pool"""
    global connection_pool
    if connection_pool:
        try:
            conn = connection_pool.getconn()
            # Testa se a conexão está ativa
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
        except Exception as e:
            logger.error(f"Erro ao obter conexão do pool: {e}")
            if conn:
                connection_pool.putconn(conn)
    return None

def return_db_connection(conn):
    """Retorna uma conexão ao pool"""
    global connection_pool
    if connection_pool and conn:
        connection_pool.putconn(conn)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerador de Schema Prisma - PostgreSQL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .spinner {
            border: 3px solid #e5e7eb;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            animation: spin 1s linear infinite;
        }
    </style>
</head>
<body class="h-full bg-slate-50">
    <div class="min-h-screen p-6 lg:p-8">
        <div class="max-w-7xl mx-auto">
            <!-- Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-semibold text-slate-900 mb-2">PostgreSQL to Prisma</h1>
                <p class="text-sm text-slate-500">Gere schemas Prisma automaticamente a partir do seu banco PostgreSQL</p>
            </div>

            <!-- Conexão -->
            <div class="bg-white rounded-lg border border-slate-200 shadow-sm mb-6">
                <div class="px-6 py-4 border-b border-slate-200">
                    <h2 class="text-lg font-medium text-slate-900">Conexão com o Banco de Dados</h2>
                </div>
                <div class="p-6">
                    <div id="connectionStatus" class="hidden mb-4 px-4 py-3 rounded-md text-sm"></div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1.5">Host</label>
                            <input type="text" id="host" value="{{ host }}"
                                   class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1.5">Porta</label>
                            <input type="number" id="port" value="{{ port }}"
                                   class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1.5">Banco de Dados</label>
                            <input type="text" id="database" value="{{ database }}"
                                   class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1.5">Usuário</label>
                            <input type="text" id="user" value="{{ user }}"
                                   class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent">
                        </div>
                    </div>

                    <div class="mb-4">
                        <label class="block text-sm font-medium text-slate-700 mb-1.5">Senha</label>
                        <input type="password" id="password" value="{{ password }}"
                               class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent">
                    </div>

                    <button id="connectBtn" onclick="connectDatabase()"
                            class="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                        Conectar
                    </button>
                </div>
            </div>

            <!-- Navegação -->
            <div id="navigationSection" class="hidden">
                <!-- Tabs -->
                <div class="bg-white rounded-lg border border-slate-200 shadow-sm mb-6">
                    <div class="border-b border-slate-200">
                        <nav class="flex -mb-px">
                            <button onclick="switchTab('schemas')" id="tabSchemas"
                                    class="tab-button active px-6 py-4 text-sm font-medium border-b-2 border-slate-900 text-slate-900">
                                Gerador de Schema
                            </button>
                            <button onclick="switchTab('dictionary')" id="tabDictionary"
                                    class="tab-button px-6 py-4 text-sm font-medium border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300">
                                Dicionário de Dados (IA)
                            </button>
                        </nav>
                    </div>
                </div>

                <!-- Tab Content: Schema Generator -->
                <div id="contentSchemas" class="tab-content">
                <div class="bg-white rounded-lg border border-slate-200 shadow-sm mb-6">
                    <div class="px-6 py-4 border-b border-slate-200">
                        <h2 class="text-lg font-medium text-slate-900">Selecione as Tabelas</h2>
                    </div>
                    <div class="p-6">
                        <!-- Campo de Busca -->
                        <div class="mb-4">
                            <div class="flex gap-2">
                                <input type="text" id="searchSchemaTable" placeholder="Buscar schema ou tabela (ex: public.users ou apenas users)"
                                       class="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                                       onkeypress="if(event.key == 'Enter') searchSchemaOrTable()">
                                <button onclick="searchSchemaOrTable()"
                                        class="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 transition-colors">
                                    Buscar
                                </button>
                            </div>
                            <div id="searchResult" class="mt-2"></div>
                        </div>

                        <div id="loadingTree" class="hidden text-center py-8">
                            <div class="spinner mx-auto mb-2"></div>
                            <p class="text-sm text-slate-500">Carregando schemas e tabelas...</p>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <!-- Lista de Tabelas -->
                            <div>
                                <div id="treeContainer" class="border border-slate-200 rounded-md p-4 max-h-96 overflow-y-auto bg-slate-50"></div>
                                <div id="selectedInfo" class="mt-3"></div>
                            </div>

                            <!-- Card de Detalhes -->
                            <div class="border border-slate-200 rounded-md">
                                <div class="px-4 py-3 border-b border-slate-200 bg-slate-50">
                                    <h3 class="text-sm font-medium text-slate-900">Detalhes da Tabela</h3>
                                </div>
                                <div id="tableDetailsContent" class="p-4">
                                    <p class="text-center text-sm text-slate-400 py-12">Selecione uma tabela para ver os detalhes</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Geração -->
                <div id="generateSection" class="hidden bg-white rounded-lg border border-slate-200 shadow-sm">
                    <div class="px-6 py-4 border-b border-slate-200">
                        <h2 class="text-lg font-medium text-slate-900">Gerar Schemas Prisma</h2>
                    </div>
                    <div class="p-6">
                        <div class="space-y-3 mb-4">
                            <label class="flex items-center">
                                <input type="radio" name="outputMode" value="multiple" checked
                                       class="w-4 h-4 text-slate-900 border-slate-300 focus:ring-slate-900">
                                <span class="ml-2 text-sm text-slate-700">Arquivo separado para cada tabela (ZIP)</span>
                            </label>
                            <label class="flex items-center">
                                <input type="radio" name="outputMode" value="single"
                                       class="w-4 h-4 text-slate-900 border-slate-300 focus:ring-slate-900">
                                <span class="ml-2 text-sm text-slate-700">Arquivo único com todas as tabelas</span>
                            </label>
                        </div>
                        <button onclick="generateSchemas()"
                                class="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 transition-colors">
                            Gerar e Baixar Schemas
                        </button>
                    </div>
                </div>
                </div>
                <!-- End Tab Content: Schema Generator -->

                <!-- Tab Content: Data Dictionary -->
                <div id="contentDictionary" class="tab-content hidden">
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <!-- Schema Selection -->
                        <div class="lg:col-span-1">
                            <div class="bg-white rounded-lg border border-slate-200 shadow-sm sticky top-6">
                                <div class="px-6 py-4 border-b border-slate-200">
                                    <h2 class="text-lg font-medium text-slate-900">Selecione os Schemas</h2>
                                </div>
                                <div class="p-6">
                                    <div id="schemasList" class="space-y-2 max-h-96 overflow-y-auto">
                                        <!-- Schema checkboxes will be populated here -->
                                    </div>
                                    <button onclick="startDictionaryChat()"
                                            class="mt-4 w-full px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 transition-colors">
                                        Iniciar Análise
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Chat Area -->
                        <div class="lg:col-span-2">
                            <div class="bg-white rounded-lg border border-slate-200 shadow-sm">
                                <div class="px-6 py-4 border-b border-slate-200">
                                    <h2 class="text-lg font-medium text-slate-900">Chat - Dicionário de Dados</h2>
                                    <p class="text-xs text-slate-500 mt-1">Converse com a IA sobre sua estrutura de banco de dados</p>
                                </div>

                                <!-- Chat Messages -->
                                <div id="chatMessages" class="p-6 h-96 overflow-y-auto bg-slate-50">
                                    <div class="text-center text-sm text-slate-400 py-12">
                                        Selecione os schemas e clique em "Iniciar Análise" para começar
                                    </div>
                                </div>

                                <!-- Chat Input -->
                                <div class="px-6 py-4 border-t border-slate-200">
                                    <div class="flex gap-2">
                                        <input type="text" id="chatInput" placeholder="Digite sua pergunta sobre o banco de dados..."
                                               class="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                                               onkeypress="if(event.key == 'Enter') sendMessage()">
                                        <button onclick="sendMessage()"
                                                class="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 transition-colors">
                                            Enviar
                                        </button>
                                    </div>
                                    <div id="chatStatus" class="mt-2 text-xs text-slate-500"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <!-- End Tab Content: Data Dictionary -->
            </div>
        </div>
    </div>

    <script>
        let schemasData = {};
        
        async function connectDatabase() {
            const status = document.getElementById('connectionStatus');
            const connectBtn = document.getElementById('connectBtn');

            connectBtn.disabled = true;
            connectBtn.textContent = 'Conectando...';

            status.className = 'block mb-4 px-4 py-3 rounded-md text-sm bg-blue-50 text-blue-700 border border-blue-200';
            status.textContent = 'Conectando ao banco de dados...';

            const params = {
                host: document.getElementById('host').value.trim(),
                port: document.getElementById('port').value.trim(),
                database: document.getElementById('database').value.trim(),
                user: document.getElementById('user').value.trim(),
                password: document.getElementById('password').value
            };

            if (!params.host || !params.port || !params.database || !params.user) {
                status.className = 'block mb-4 px-4 py-3 rounded-md text-sm bg-red-50 text-red-700 border border-red-200';
                status.textContent = 'Por favor, preencha todos os campos obrigatórios';
                connectBtn.disabled = false;
                connectBtn.textContent = 'Conectar';
                return;
            }

            try {
                const response = await fetch('/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });

                const result = await response.json();

                if (result.success) {
                    status.className = 'block mb-4 px-4 py-3 rounded-md text-sm bg-green-50 text-green-700 border border-green-200';
                    status.textContent = 'Conectado com sucesso!';
                    document.getElementById('navigationSection').classList.remove('hidden');
                    connectBtn.textContent = 'Reconectar';
                    loadSchemas();
                } else {
                    status.className = 'block mb-4 px-4 py-3 rounded-md text-sm bg-red-50 text-red-700 border border-red-200';
                    status.textContent = 'Erro: ' + (result.error || 'Erro desconhecido');
                    connectBtn.textContent = 'Conectar';
                }
            } catch (error) {
                status.className = 'block mb-4 px-4 py-3 rounded-md text-sm bg-red-50 text-red-700 border border-red-200';
                status.textContent = 'Erro de conexão: ' + error.message;
                connectBtn.textContent = 'Conectar';
            } finally {
                connectBtn.disabled = false;
            }
        }

        async function loadSchemas() {
            const loading = document.getElementById('loadingTree');
            const container = document.getElementById('treeContainer');

            loading.classList.remove('hidden');
            container.innerHTML = '';

            try {
                const response = await fetch('/schemas');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                schemasData = await response.json();
                loading.classList.add('hidden');
                renderTree();
            } catch (error) {
                loading.classList.add('hidden');
                container.innerHTML = '<p class="text-sm text-red-600">Erro ao carregar schemas: ' + error.message + '</p>';
            }
        }

        function renderTree() {
            const container = document.getElementById('treeContainer');
            container.innerHTML = '';

            if (Object.keys(schemasData).length === 0) {
                container.innerHTML = '<p class="text-sm text-slate-400">Nenhuma tabela encontrada no banco de dados.</p>';
                return;
            }

            for (const [schema, tables] of Object.entries(schemasData)) {
                const schemaDiv = document.createElement('div');
                schemaDiv.className = 'mb-3';

                const schemaHeader = document.createElement('div');
                schemaHeader.className = 'flex items-center justify-between bg-slate-900 text-white px-3 py-2 rounded-md cursor-pointer hover:bg-slate-800 transition-colors';
                schemaHeader.innerHTML = `
                    <span class="text-sm font-medium">📁 ${schema}</span>
                    <span class="text-xs bg-slate-700 px-2 py-0.5 rounded">${tables.length}</span>
                `;
                schemaHeader.onclick = () => toggleSchema(schema);

                const tablesList = document.createElement('div');
                tablesList.className = 'hidden mt-2 ml-4 space-y-1';
                tablesList.id = `tables-${schema}`;

                tables.forEach(table => {
                    const tableItem = document.createElement('div');
                    tableItem.className = 'flex items-center gap-2 px-3 py-2 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors';
                    tableItem.innerHTML = `
                        <input type="checkbox" id="cb-${schema}-${table}"
                               onchange="updateSelection(event)"
                               class="w-4 h-4 text-slate-900 border-slate-300 rounded focus:ring-slate-900">
                        <label for="cb-${schema}-${table}" class="text-sm text-slate-700 cursor-pointer flex-1">📄 ${table}</label>
                    `;
                    tablesList.appendChild(tableItem);
                });

                schemaDiv.appendChild(schemaHeader);
                schemaDiv.appendChild(tablesList);
                container.appendChild(schemaDiv);
            }

            const firstSchema = Object.keys(schemasData)[0];
            if (firstSchema) {
                toggleSchema(firstSchema);
            }
        }

        function toggleSchema(schema) {
            const tablesList = document.getElementById(`tables-${schema}`);
            if (tablesList) {
                tablesList.classList.toggle('hidden');
            }
        }

        async function updateSelection(event) {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
            const count = checkboxes.length;

            const info = document.getElementById('selectedInfo');
            if (count > 0) {
                info.innerHTML = `<div class="inline-flex items-center px-3 py-1.5 bg-slate-900 text-white text-sm rounded-md">${count} tabela(s) selecionada(s)</div>`;
                document.getElementById('generateSection').classList.remove('hidden');

                if (event && event.target && event.target.checked) {
                    const checkboxId = event.target.id;
                    const parts = checkboxId.replace('cb-', '').split('-');
                    const schema = parts[0];
                    const table = parts.slice(1).join('-');
                    await showTableDetails(schema, table);
                }
            } else {
                info.innerHTML = '';
                document.getElementById('generateSection').classList.add('hidden');
                const detailsContent = document.getElementById('tableDetailsContent');
                detailsContent.innerHTML = '<p class="text-center text-sm text-slate-400 py-12">Selecione uma tabela para ver os detalhes</p>';
            }
        }

        async function showTableDetails(schema, table) {
            const detailsContent = document.getElementById('tableDetailsContent');
            detailsContent.innerHTML = '<div class="text-center py-8"><div class="spinner mx-auto mb-2"></div><p class="text-sm text-slate-500">Carregando...</p></div>';

            try {
                const response = await fetch('/table-details', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({schema: schema, table: table})
                });

                const details = await response.json();

                if (details.error) {
                    detailsContent.innerHTML = `<p class="text-sm text-red-600">Erro: ${details.error}</p>`;
                    return;
                }

                detailsContent.innerHTML = `
                    <div class="mb-4 p-3 bg-slate-50 rounded-md border border-slate-200 text-sm">
                        <span class="font-medium text-slate-700">Database:</span> <span class="text-slate-600">${details.database}</span> |
                        <span class="font-medium text-slate-700">Schema:</span> <span class="text-slate-600">${details.schema}</span> |
                        <span class="font-medium text-slate-700">Tabela:</span> <span class="text-slate-600">${details.table}</span> |
                        <span class="font-medium text-slate-700">FDW:</span> <span class="text-slate-600">${details.fdw}</span>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-slate-700 mb-2">DDL:</div>
                        <div class="bg-slate-900 text-slate-50 p-4 rounded-md font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto">${details.ddl}</div>
                    </div>
                `;
            } catch (error) {
                detailsContent.innerHTML = `<p class="text-sm text-red-600">Erro ao carregar detalhes: ${error.message}</p>`;
            }
        }

        async function generateSchemas() {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
            const selected = [];

            checkboxes.forEach(cb => {
                const parts = cb.id.replace('cb-', '').split('-');
                selected.push({
                    schema: parts[0],
                    table: parts.slice(1).join('-')
                });
            });

            if (selected.length === 0) {
                alert('Selecione pelo menos uma tabela!');
                return;
            }

            const outputMode = document.querySelector('input[name="outputMode"]:checked').value;

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        tables: selected,
                        mode: outputMode
                    })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = outputMode === 'single' ? 'schema.prisma' : 'prisma-schemas.zip';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    const error = await response.text();
                    alert('Erro ao gerar schemas: ' + error);
                }
            } catch (error) {
                alert('Erro: ' + error.message);
            }
        }

        async function searchSchemaOrTable() {
            const input = document.getElementById('searchSchemaTable');
            const searchValue = input.value.trim();
            const resultDiv = document.getElementById('searchResult');

            if (!searchValue) {
                resultDiv.innerHTML = '<p class="text-sm text-slate-500">Digite um schema ou tabela para buscar</p>';
                return;
            }

            resultDiv.innerHTML = '<div class="flex items-center gap-2 text-sm text-slate-500"><div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>Buscando...</div>';

            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: searchValue})
                });

                const result = await response.json();

                if (response.ok) {
                    let html = '';

                    if (result.schema_found) {
                        html += `<div class="p-3 bg-green-50 border border-green-200 rounded-md text-sm">
                            <p class="text-green-900"><strong>✓ Schema encontrado:</strong> ${result.schema}</p>
                            <p class="text-green-700 mt-1">${result.table_count} tabela(s) neste schema</p>
                        </div>`;
                    }

                    if (result.tables && result.tables.length > 0) {
                        html += `<div class="p-3 bg-green-50 border border-green-200 rounded-md text-sm">
                            <p class="text-green-900 mb-2"><strong>✓ ${result.tables.length} tabela(s) encontrada(s):</strong></p>
                            <ul class="space-y-1">`;

                        result.tables.forEach(item => {
                            html += `<li class="text-green-800">• <span class="font-mono">${item.schema}.${item.table}</span></li>`;
                        });

                        html += `</ul></div>`;
                    }

                    if (!result.schema_found && (!result.tables || result.tables.length === 0)) {
                        html += `<div class="p-3 bg-red-50 border border-red-200 rounded-md text-sm">
                            <p class="text-red-900"><strong>✗ Não encontrado:</strong> ${searchValue}</p>
                        </div>`;
                    }

                    resultDiv.innerHTML = html;
                } else {
                    resultDiv.innerHTML = `<div class="p-3 bg-red-50 border border-red-200 rounded-md text-sm">
                        <p class="text-red-900">Erro: ${result.error}</p>
                    </div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="p-3 bg-red-50 border border-red-200 rounded-md text-sm">
                    <p class="text-red-900">Erro: ${error.message}</p>
                </div>`;
            }
        }

        // ===== DATA DICTIONARY FUNCTIONS =====

        let conversationHistory = [];
        let selectedSchemas = [];

        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active', 'border-slate-900', 'text-slate-900');
                btn.classList.add('border-transparent', 'text-slate-500');
            });

            if (tabName === 'schemas') {
                document.getElementById('tabSchemas').classList.add('active', 'border-slate-900', 'text-slate-900');
                document.getElementById('tabSchemas').classList.remove('border-transparent', 'text-slate-500');
            } else {
                document.getElementById('tabDictionary').classList.add('active', 'border-slate-900', 'text-slate-900');
                document.getElementById('tabDictionary').classList.remove('border-transparent', 'text-slate-500');
            }

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.add('hidden');
            });

            if (tabName === 'schemas') {
                document.getElementById('contentSchemas').classList.remove('hidden');
            } else {
                document.getElementById('contentDictionary').classList.remove('hidden');
                loadSchemasForDictionary();
            }
        }

        function loadSchemasForDictionary() {
            const container = document.getElementById('schemasList');

            if (Object.keys(schemasData).length === 0) {
                container.innerHTML = '<p class="text-sm text-slate-400">Nenhum schema disponível</p>';
                return;
            }

            container.innerHTML = '';

            for (const schema of Object.keys(schemasData)) {
                const schemaDiv = document.createElement('div');
                schemaDiv.className = 'flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-md';
                schemaDiv.innerHTML = `
                    <input type="checkbox" id="schema-${schema}" value="${schema}"
                           class="w-4 h-4 text-slate-900 border-slate-300 rounded focus:ring-slate-900">
                    <label for="schema-${schema}" class="text-sm text-slate-700 cursor-pointer flex-1">
                        📁 ${schema} <span class="text-xs text-slate-500">(${schemasData[schema].length} tabelas)</span>
                    </label>
                `;
                container.appendChild(schemaDiv);
            }
        }

        async function startDictionaryChat() {
            const checkboxes = document.querySelectorAll('#schemasList input[type="checkbox"]:checked');
            selectedSchemas = Array.from(checkboxes).map(cb => cb.value);

            if (selectedSchemas.length === 0) {
                alert('Selecione pelo menos um schema!');
                return;
            }

            // Clear chat
            conversationHistory = [];
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                    <p class="text-sm text-blue-900">
                        <strong>Schemas selecionados:</strong> ${selectedSchemas.join(', ')}
                    </p>
                    <p class="text-xs text-blue-700 mt-2">
                        Faça perguntas sobre a estrutura do banco de dados, relacionamentos entre tabelas, ou peça uma análise geral.
                    </p>
                </div>
            `;

            // Enable input
            document.getElementById('chatInput').disabled = false;
            document.getElementById('chatInput').focus();
        }

        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();

            if (!message) return;

            if (selectedSchemas.length === 0) {
                alert('Primeiro inicie a análise selecionando os schemas!');
                return;
            }

            // Add user message to chat
            addMessageToChat('user', message);
            input.value = '';

            // Show loading
            const status = document.getElementById('chatStatus');
            status.textContent = 'Aguardando resposta da IA...';
            status.className = 'mt-2 text-xs text-blue-600';

            try {
                const response = await fetch('/api/data-dictionary/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        schemas: selectedSchemas,
                        history: conversationHistory
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Add assistant message
                    addMessageToChat('assistant', data.message);

                    // Update conversation history
                    conversationHistory.push({role: 'user', content: message});
                    conversationHistory.push({role: 'assistant', content: data.message});

                    // Update status with token usage
                    status.textContent = `Tokens: ${data.usage.input_tokens} entrada, ${data.usage.output_tokens} saída | Modelo: ${data.model}`;
                    status.className = 'mt-2 text-xs text-slate-500';
                } else {
                    status.textContent = 'Erro: ' + data.error;
                    status.className = 'mt-2 text-xs text-red-600';

                    addMessageToChat('system', '❌ Erro: ' + data.error);
                }
            } catch (error) {
                status.textContent = 'Erro de conexão: ' + error.message;
                status.className = 'mt-2 text-xs text-red-600';

                addMessageToChat('system', '❌ Erro de conexão: ' + error.message);
            }
        }

        function addMessageToChat(role, content) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'mb-4';

            if (role === 'user') {
                messageDiv.innerHTML = `
                    <div class="flex justify-end">
                        <div class="max-w-3xl px-4 py-2 bg-slate-900 text-white rounded-lg">
                            <p class="text-sm whitespace-pre-wrap">${escapeHtml(content)}</p>
                        </div>
                    </div>
                `;
            } else if (role === 'assistant') {
                messageDiv.innerHTML = `
                    <div class="flex justify-start">
                        <div class="max-w-3xl px-4 py-2 bg-white border border-slate-200 rounded-lg">
                            <div class="text-sm prose prose-sm max-w-none">${formatMarkdown(content)}</div>
                        </div>
                    </div>
                `;
            } else if (role === 'system') {
                messageDiv.innerHTML = `
                    <div class="px-4 py-2 bg-red-50 border border-red-200 rounded-lg">
                        <p class="text-sm text-red-900">${escapeHtml(content)}</p>
                    </div>
                `;
            }

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatMarkdown(text) {
            // Escape HTML first
            const div = document.createElement('div');
            div.textContent = text;
            let formatted = div.innerHTML;

            // Bold: **text**
            formatted = formatted.split('**').map(function(part, i) {
                return i % 2 == 1 ? '<strong>' + part + '</strong>' : part;
            }).join('');

            // Inline code: `code`
            formatted = formatted.split('`').map(function(part, i) {
                return i % 2 == 1 ? '<code class="px-1 py-0.5 bg-slate-100 rounded text-xs font-mono">' + part + '</code>' : part;
            }).join('');

            // Replace line breaks with <br>
            formatted = formatted.split('\\n').join('<br>');

            return formatted;
        }
    </script>
</body>
</html>
'''

def extract_database_metadata(conn, selected_schemas=None):
    """
    Extrai metadados completos do banco de dados incluindo schemas, tabelas, colunas,
    constraints, relacionamentos e índices.

    Args:
        conn: Conexão com o banco de dados PostgreSQL
        selected_schemas: Lista de schemas a extrair. Se None, extrai todos (exceto system schemas)

    Returns:
        dict: Metadados estruturados do banco de dados
    """
    cursor = None
    try:
        cursor = conn.cursor()
        metadata = {
            'database_name': '',
            'schemas': {}
        }

        # Nome do banco de dados
        cursor.execute("SELECT current_database()")
        metadata['database_name'] = cursor.fetchone()[0]

        # Query para buscar schemas
        schema_filter = ""
        if selected_schemas:
            schema_placeholders = ','.join(['%s'] * len(selected_schemas))
            schema_filter = f"AND table_schema IN ({schema_placeholders})"

        # Busca todas as tabelas dos schemas selecionados
        query = f"""
            SELECT DISTINCT table_schema
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_type = 'BASE TABLE'
              {schema_filter}
            ORDER BY table_schema
        """

        if selected_schemas:
            cursor.execute(query, tuple(selected_schemas))
        else:
            cursor.execute(query)

        schemas = [row[0] for row in cursor.fetchall()]

        for schema_name in schemas:
            metadata['schemas'][schema_name] = {'tables': {}}

            # Busca tabelas do schema
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (schema_name,))

            tables = [row[0] for row in cursor.fetchall()]

            for table_name in tables:
                table_metadata = {
                    'columns': [],
                    'primary_keys': [],
                    'foreign_keys': [],
                    'indexes': [],
                    'constraints': []
                }

                # Busca colunas
                cursor.execute("""
                    SELECT
                        column_name,
                        data_type,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema_name, table_name))

                for row in cursor.fetchall():
                    col_name, data_type, char_len, num_prec, num_scale, is_nullable, col_default, ordinal_pos = row

                    type_detail = data_type
                    if char_len:
                        type_detail += f"({char_len})"
                    elif num_prec:
                        if num_scale:
                            type_detail += f"({num_prec},{num_scale})"
                        else:
                            type_detail += f"({num_prec})"

                    table_metadata['columns'].append({
                        'name': col_name,
                        'type': data_type,
                        'type_detail': type_detail,
                        'nullable': is_nullable == 'YES',
                        'default': col_default,
                        'position': ordinal_pos
                    })

                # Busca chaves primárias
                cursor.execute("""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass AND i.indisprimary
                    ORDER BY array_position(i.indkey, a.attnum)
                """, (f'{schema_name}.{table_name}',))

                table_metadata['primary_keys'] = [row[0] for row in cursor.fetchall()]

                # Busca chaves estrangeiras
                cursor.execute("""
                    SELECT
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_schema AS foreign_schema,
                        ccu.table_name AS foreign_table,
                        ccu.column_name AS foreign_column
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = %s
                        AND tc.table_name = %s
                """, (schema_name, table_name))

                for row in cursor.fetchall():
                    constraint_name, column_name, foreign_schema, foreign_table, foreign_column = row
                    table_metadata['foreign_keys'].append({
                        'constraint_name': constraint_name,
                        'column': column_name,
                        'references_schema': foreign_schema,
                        'references_table': foreign_table,
                        'references_column': foreign_column
                    })

                # Busca índices
                cursor.execute("""
                    SELECT
                        i.relname AS index_name,
                        a.attname AS column_name,
                        ix.indisunique AS is_unique,
                        ix.indisprimary AS is_primary
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    WHERE n.nspname = %s
                        AND t.relname = %s
                        AND NOT ix.indisprimary
                    ORDER BY i.relname, a.attnum
                """, (schema_name, table_name))

                indexes = {}
                for row in cursor.fetchall():
                    index_name, column_name, is_unique, is_primary = row
                    if index_name not in indexes:
                        indexes[index_name] = {
                            'name': index_name,
                            'columns': [],
                            'unique': is_unique
                        }
                    indexes[index_name]['columns'].append(column_name)

                table_metadata['indexes'] = list(indexes.values())

                # Busca outras constraints (UNIQUE, CHECK)
                cursor.execute("""
                    SELECT
                        tc.constraint_name,
                        tc.constraint_type,
                        kcu.column_name
                    FROM information_schema.table_constraints AS tc
                    LEFT JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.table_schema = %s
                        AND tc.table_name = %s
                        AND tc.constraint_type IN ('UNIQUE', 'CHECK')
                    ORDER BY tc.constraint_name
                """, (schema_name, table_name))

                constraints = {}
                for row in cursor.fetchall():
                    constraint_name, constraint_type, column_name = row
                    if constraint_name not in constraints:
                        constraints[constraint_name] = {
                            'name': constraint_name,
                            'type': constraint_type,
                            'columns': []
                        }
                    if column_name:
                        constraints[constraint_name]['columns'].append(column_name)

                table_metadata['constraints'] = list(constraints.values())

                metadata['schemas'][schema_name]['tables'][table_name] = table_metadata

        return metadata
    finally:
        if cursor:
            cursor.close()

def schema_exists(conn, schema_name):
    """
    Verifica se um schema existe no banco de dados.

    Args:
        conn: Conexão com o banco de dados PostgreSQL
        schema_name: Nome do schema a verificar

    Returns:
        bool: True se o schema existe, False caso contrário
    """
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1
                FROM information_schema.schemata
                WHERE schema_name = %s
            )
        """, (schema_name,))

        return cursor.fetchone()[0]
    finally:
        if cursor:
            cursor.close()

def table_exists(conn, schema_name, table_name):
    """
    Verifica se uma tabela existe em um schema específico.

    Args:
        conn: Conexão com o banco de dados PostgreSQL
        schema_name: Nome do schema onde procurar
        table_name: Nome da tabela a verificar

    Returns:
        bool: True se a tabela existe, False caso contrário
    """
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
                  AND table_type = 'BASE TABLE'
            )
        """, (schema_name, table_name))

        return cursor.fetchone()[0]
    finally:
        if cursor:
            cursor.close()

def map_postgres_to_prisma_type(pg_type):
    """Mapeia tipos PostgreSQL para tipos Prisma"""
    type_mapping = {
        'integer': 'Int',
        'bigint': 'BigInt',
        'smallint': 'Int',
        'serial': 'Int',
        'bigserial': 'BigInt',
        'numeric': 'Decimal',
        'decimal': 'Decimal',
        'real': 'Float',
        'double precision': 'Float',
        'money': 'Decimal',
        'character varying': 'String',
        'varchar': 'String',
        'character': 'String',
        'char': 'String',
        'text': 'String',
        'boolean': 'Boolean',
        'date': 'DateTime',
        'timestamp': 'DateTime',
        'timestamp without time zone': 'DateTime',
        'timestamp with time zone': 'DateTime',
        'time': 'DateTime',
        'json': 'Json',
        'jsonb': 'Json',
        'uuid': 'String',
        'bytea': 'Bytes',
    }
    return type_mapping.get(pg_type.lower(), 'String')

def generate_prisma_schema(schema_name, table_name, conn):
    """Gera o schema Prisma para uma tabela específica"""
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Busca colunas da tabela
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table_name))
        
        columns = cursor.fetchall()
        
        # Busca chaves primárias
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """, (f'{schema_name}.{table_name}',))
        
        primary_keys = [row[0] for row in cursor.fetchall()]
        
        # Gera o modelo Prisma
        model_name = ''.join(word.capitalize() for word in table_name.split('_'))
        
        prisma_schema = f'model {model_name} {{\n'
        
        for col_name, data_type, is_nullable, col_default in columns:
            prisma_type = map_postgres_to_prisma_type(data_type)
            optional = '?' if is_nullable == 'YES' and col_name not in primary_keys else ''
            
            attributes = []
            if col_name in primary_keys:
                attributes.append('@id')
            if col_default and 'nextval' in str(col_default):
                attributes.append('@default(autoincrement())')
            elif col_default:
                if 'now()' in str(col_default) or 'CURRENT_TIMESTAMP' in str(col_default):
                    attributes.append('@default(now())')
            
            attr_str = ' ' + ' '.join(attributes) if attributes else ''
            prisma_schema += f'  {col_name} {prisma_type}{optional}{attr_str}\n'
        
        prisma_schema += f'\n  @@map("{table_name}")\n'
        if schema_name != 'public':
            prisma_schema += f'  @@schema("{schema_name}")\n'
        prisma_schema += '}\n'
        
        return prisma_schema
    finally:
        if cursor:
            cursor.close()

@app.route('/')
def index():
    config = load_config()
    return render_template_string(HTML_TEMPLATE,
                                   host=config.get('host', 'localhost'),
                                   port=config.get('port', '5432'),
                                   database=config.get('database', 'postgres'),
                                   user=config.get('user', 'postgres'),
                                   password=config.get('password', ''))

@app.route('/connect', methods=['POST'])
def connect():
    global connection_pool
    try:
        params = request.json
        logger.info(f"Tentando conectar com: host={params['host']}, port={params['port']}, database={params['database']}, user={params['user']}")
        
        # Validação dos parâmetros
        if not all([params.get('host'), params.get('port'), params.get('database'), params.get('user')]):
            return jsonify({'success': False, 'error': 'Parâmetros incompletos'})
        
        # Fecha pool anterior se existir
        if connection_pool:
            try:
                connection_pool.closeall()
            except:
                pass
        
        # Cria novo pool de conexões
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 5,  # min e max conexões
            host=params['host'],
            port=int(params['port']),
            database=params['database'],
            user=params['user'],
            password=params['password']
        )
        
        # Testa a conexão
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        logger.info(f"Conectado ao PostgreSQL: {version[0]}")
        cursor.close()
        connection_pool.putconn(conn)
        
        save_config(params)
        return jsonify({'success': True, 'message': 'Conexão estabelecida com sucesso'})
        
    except psycopg2.OperationalError as e:
        logger.error(f"Erro operacional do PostgreSQL: {e}")
        return jsonify({'success': False, 'error': f'Erro de conexão: {str(e)}'})
    except Exception as e:
        logger.error(f"Erro ao conectar: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/schemas')
def get_schemas():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                table_schema,
                table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_type = 'BASE TABLE'
              AND table_name !~ '(_p|p_|_)[0-9]+$'
            ORDER BY table_schema, table_name
        """)

        results = cursor.fetchall()
        schemas = {}

        for schema, table in results:
            if schema not in schemas:
                schemas[schema] = []
            schemas[schema].append(table)

        cursor.close()
        return_db_connection(conn)

        return jsonify(schemas)
    except Exception as e:
        logger.error(f"Erro ao buscar schemas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/table-details', methods=['POST'])
def table_details():
    conn = None
    try:
        data = request.json
        schema_name = data['schema']
        table_name = data['table']

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        cursor = conn.cursor()

        # Busca o nome do banco de dados
        cursor.execute("SELECT current_database()")
        database_name = cursor.fetchone()[0]

        # Verifica se é Foreign Data Wrapper
        cursor.execute("""
            SELECT c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
        """, (schema_name, table_name))

        result = cursor.fetchone()
        is_fdw = 'Sim' if result and result[0] == 'f' else 'Não'

        # Gera DDL da tabela
        cursor.execute("""
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table_name))

        columns = cursor.fetchall()

        # Busca constraints (chave primária)
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """, (f'{schema_name}.{table_name}',))

        primary_keys = [row[0] for row in cursor.fetchall()]

        # Gera DDL
        ddl = f"CREATE TABLE {schema_name}.{table_name} (\n"
        col_defs = []

        for col_name, data_type, char_len, num_prec, num_scale, is_nullable, col_default in columns:
            col_def = f"  {col_name} {data_type.upper()}"

            if char_len:
                col_def += f"({char_len})"
            elif num_prec:
                if num_scale:
                    col_def += f"({num_prec},{num_scale})"
                else:
                    col_def += f"({num_prec})"

            if is_nullable == 'NO':
                col_def += " NOT NULL"

            if col_default:
                col_def += f" DEFAULT {col_default}"

            col_defs.append(col_def)

        if primary_keys:
            pk_str = ", ".join(primary_keys)
            col_defs.append(f"  PRIMARY KEY ({pk_str})")

        ddl += ",\n".join(col_defs)
        ddl += "\n);"

        cursor.close()

        return jsonify({
            'database': database_name,
            'schema': schema_name,
            'table': table_name,
            'fdw': is_fdw,
            'ddl': ddl
        })
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da tabela: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/search', methods=['POST'])
def search():
    """Busca por schema ou tabela no banco de dados (exata ou parcial)"""
    conn = None
    try:
        data = request.json
        query = data.get('query', '').strip()

        if not query:
            return jsonify({'error': 'Query vazia'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        cursor = conn.cursor()
        result_data = {
            'schema_found': False,
            'tables': []
        }

        # Verifica se a query contém ponto (schema.tabela)
        if '.' in query:
            parts = query.split('.')
            schema_name = parts[0].strip()
            table_name = parts[1].strip()

            # Busca exata
            cursor.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
                  AND table_type = 'BASE TABLE'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_name !~ '(_p|p_|_)[0-9]+$'
            """, (schema_name, table_name))

            exact_match = cursor.fetchone()

            if exact_match:
                result_data['tables'].append({
                    'schema': exact_match[0],
                    'table': exact_match[1]
                })
            else:
                # Busca parcial no schema especificado
                cursor.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                      AND table_name ILIKE %s
                      AND table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_name !~ '(_p|p_|_)[0-9]+$'
                    ORDER BY table_name
                """, (schema_name, f'%{table_name}%'))

                for row in cursor.fetchall():
                    result_data['tables'].append({
                        'schema': row[0],
                        'table': row[1]
                    })
        else:
            # Primeiro tenta como schema
            if schema_exists(conn, query):
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = %s
                      AND table_type = 'BASE TABLE'
                """, (query,))
                table_count = cursor.fetchone()[0]

                result_data['schema_found'] = True
                result_data['schema'] = query
                result_data['table_count'] = table_count

            # Busca exata de tabelas em todos os schemas
            cursor.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = %s
                  AND table_type = 'BASE TABLE'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_name !~ '(_p|p_|_)[0-9]+$'
                ORDER BY table_schema, table_name
            """, (query,))

            exact_matches = cursor.fetchall()
            for row in exact_matches:
                result_data['tables'].append({
                    'schema': row[0],
                    'table': row[1]
                })

            # Se não encontrou nada exato, busca parcial
            if not result_data['schema_found'] and len(result_data['tables']) == 0:
                cursor.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_name ILIKE %s
                      AND table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_name !~ '(_p|p_|_)[0-9]+$'
                    ORDER BY table_schema, table_name
                    LIMIT 50
                """, (f'%{query}%',))

                for row in cursor.fetchall():
                    result_data['tables'].append({
                        'schema': row[0],
                        'table': row[1]
                    })

        cursor.close()
        return jsonify(result_data)

    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/generate', methods=['POST'])
def generate():
    conn = None
    try:
        data = request.json
        tables = data['tables']
        mode = data.get('mode', 'multiple')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        if mode == 'single':
            # Gera um único arquivo com todas as tabelas
            prisma_content = "// Schema Prisma gerado automaticamente\n"
            prisma_content += f"// Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            for item in tables:
                schema = item['schema']
                table = item['table']
                prisma_content += generate_prisma_schema(schema, table, conn)
                prisma_content += "\n"

            # Retorna o arquivo único
            buffer = io.BytesIO()
            buffer.write(prisma_content.encode('utf-8'))
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype='text/plain',
                as_attachment=True,
                download_name='schema.prisma'
            )
        else:
            # Cria um arquivo ZIP com múltiplos arquivos
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for item in tables:
                    schema = item['schema']
                    table = item['table']

                    prisma_content = generate_prisma_schema(schema, table, conn)
                    filename_zip = f'{schema}_{table}.prisma'
                    zip_file.writestr(filename_zip, prisma_content)

            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'prisma-schemas-{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
            )
    except Exception as e:
        logger.error(f"Erro ao gerar schemas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/api/data-dictionary/metadata', methods=['POST'])
def get_data_dictionary_metadata():
    """Obtém metadados completos dos schemas/tabelas selecionados"""
    conn = None
    try:
        data = request.json
        selected_schemas = data.get('schemas', [])

        if not selected_schemas:
            return jsonify({'error': 'Nenhum schema selecionado'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        metadata = extract_database_metadata(conn, selected_schemas)
        return jsonify(metadata)

    except Exception as e:
        logger.error(f"Erro ao buscar metadados: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/api/data-dictionary/chat', methods=['POST'])
def chat_data_dictionary():
    """Endpoint para chat com Grok sobre o dicionário de dados"""
    conn = None
    try:
        if not grok_client:
            return jsonify({
                'error': 'Serviço de IA não disponível. Configure XAI_API_KEY no arquivo .env'
            }), 503

        data = request.json
        user_message = data.get('message', '').strip()
        selected_schemas = data.get('schemas', [])
        conversation_history = data.get('history', [])

        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400

        if not selected_schemas:
            return jsonify({'error': 'Nenhum schema selecionado'}), 400

        # Obtém metadados do banco de dados
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Não conectado ao banco de dados'}), 500

        metadata = extract_database_metadata(conn, selected_schemas)

        # Prepara contexto para o Grok
        context = f"""Você é um especialista em bancos de dados PostgreSQL e está analisando o seguinte banco de dados:

**Banco de Dados:** {metadata['database_name']}

**Estrutura do Banco de Dados:**

"""

        # Adiciona informações detalhadas sobre cada schema/tabela
        for schema_name, schema_data in metadata['schemas'].items():
            context += f"\n### Schema: {schema_name}\n\n"

            for table_name, table_data in schema_data['tables'].items():
                context += f"#### Tabela: {table_name}\n\n"

                # Colunas
                context += "**Colunas:**\n"
                for col in table_data['columns']:
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    default = f", DEFAULT: {col['default']}" if col['default'] else ""
                    context += f"- `{col['name']}` {col['type_detail']} {nullable}{default}\n"

                # Chave primária
                if table_data['primary_keys']:
                    context += f"\n**Chave Primária:** {', '.join(table_data['primary_keys'])}\n"

                # Chaves estrangeiras
                if table_data['foreign_keys']:
                    context += "\n**Chaves Estrangeiras:**\n"
                    for fk in table_data['foreign_keys']:
                        context += f"- `{fk['column']}` → `{fk['references_schema']}.{fk['references_table']}.{fk['references_column']}`\n"

                # Índices
                if table_data['indexes']:
                    context += "\n**Índices:**\n"
                    for idx in table_data['indexes']:
                        unique = "UNIQUE" if idx['unique'] else ""
                        context += f"- {idx['name']} {unique} ({', '.join(idx['columns'])})\n"

                # Constraints
                if table_data['constraints']:
                    context += "\n**Constraints:**\n"
                    for const in table_data['constraints']:
                        cols = f"({', '.join(const['columns'])})" if const['columns'] else ""
                        context += f"- {const['name']} ({const['type']}) {cols}\n"

                context += "\n"

        context += """

**Sua tarefa é:**
1. Analisar a estrutura do banco de dados acima
2. Explicar o propósito e significado dos schemas, tabelas e campos
3. Identificar e explicar os relacionamentos entre as tabelas
4. Sugerir prováveis casos de uso e finalidades do banco de dados
5. Responder perguntas do usuário sobre a estrutura do banco de dados

**Diretrizes:**
- Seja claro e didático nas explicações
- Use exemplos quando apropriado
- Identifique padrões de design (normalização, denormalização, etc)
- Sugira melhorias quando relevante
- Explique em português brasileiro
"""

        # Monta histórico de mensagens no formato OpenAI
        messages = [
            {"role": "system", "content": context}
        ]

        # Adiciona histórico de conversação se houver
        for msg in conversation_history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # Adiciona mensagem atual do usuário
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Chama a API do Grok (formato OpenAI)
        response = grok_client.chat.completions.create(
            model="grok-3",
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content

        return jsonify({
            'message': assistant_message,
            'model': response.model,
            'usage': {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens
            }
        })

    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            return_db_connection(conn)

@app.route('/favicon.ico')
def favicon():
    """Retorna 204 No Content para evitar erro 500 no favicon"""
    return '', 204

@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Erro não tratado: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("🚀 Servidor iniciado em http://localhost:5000")
    print("📝 Acesse o navegador para usar a aplicação")
    print("🔍 Logs habilitados para debug")
    app.run(debug=True, host='0.0.0.0', port=5000)
