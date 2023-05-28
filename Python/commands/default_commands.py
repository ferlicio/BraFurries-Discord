from datetime import date
import re

invalid = "Entrada inválida"

def calcular_idade (message):
    pattern = r"[^0-9/]"
    if not (re.search(pattern, message)):        
        message = message.split('/')
        if int(message[1]) > 12 or int(message[1]) < 1 or int(message[0]) > 31 or int(message[0]) < 1:
            return invalid
        data_nascimento = date(int(message[2]), int(message[1]), int(message[0]))
        data_atual = date.today()
        idade = data_atual.year - data_nascimento.year
        # Verificar se já fez aniversário neste ano
        if data_atual.month < data_nascimento.month or (data_atual.month == data_nascimento.month and data_atual.day < data_nascimento.day):
            idade -= 1
        return idade
    return invalid
