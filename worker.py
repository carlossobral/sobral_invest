import time
import requests

while True:
    try:
        # Chama o endpoint /atualizar da sua API
        requests.get("https://sobral-invest-b5ua.onrender.com/atualizar")
        print("Dados atualizados com sucesso!")
    except Exception as e:
        print("Erro ao atualizar:", e)

    # Espera 1 hora antes da próxima atualização
    time.sleep(3600)
