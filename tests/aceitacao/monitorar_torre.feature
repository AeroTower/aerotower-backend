# language: pt
Funcionalidade: Monitorar e controlar a minha torre pelo app
  Como dono de uma torre AeroTower
  Quero ver as leituras da minha torre e comandar a bomba
  Para cuidar das plantas sem estar perto da torre

  Contexto:
    Dado que a Maria tem uma torre do kit "pro" vinculada à conta dela

  Cenário: Leitura fora da faixa vira alerta no painel
    Quando a torre publica pH 7.4 e nível de água 20
    Então o painel da Maria mostra o alerta "pH acima"
    E o painel da Maria mostra o alerta "Nível de água baixo"

  Cenário: Leitura dentro da faixa não gera alerta
    Quando a torre publica pH 6.0 e nível de água 80
    Então o painel da Maria não mostra nenhum alerta

  Cenário: Maria programa o ciclo da bomba
    Quando a Maria pede um ciclo de 15 minutos ligada e 45 desligada
    Então a torre recebe o comando de ciclo com 15 e 45 minutos

  Cenário: Outra pessoa não enxerga a torre da Maria
    Quando o João tenta abrir o painel da torre da Maria
    Então o João recebe "não encontrada"

  Cenário: Torre do kit básico só mostra a bomba
    Dado que a Maria também tem uma torre do kit "basico"
    Quando a torre básica publica pH 3.0 e o motor ligado
    Então o painel da torre básica mostra só os dados da bomba
