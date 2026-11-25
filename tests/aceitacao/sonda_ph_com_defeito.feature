# language: pt
# CT-ACEIT-02 (teste individual). Corrigido na refatoracao: agora passa e protege contra a volta do defeito.
Funcionalidade: Avisar quando a sonda de pH está com defeito
  Como dono de uma torre AeroTower
  Quero saber quando a leitura de pH é impossível
  Para trocar a sonda em vez de colocar produto na água à toa

  Contexto:
    Dado que a Maria tem uma torre do kit "pro" vinculada à conta dela

  Esquema do Cenário: Sonda de pH solta ou em curto
    Quando a torre publica pH <ph> e nível de água 80
    Então o painel da Maria avisa que o sensor de pH está com defeito
    E o painel da Maria não manda corrigir o pH da água

    Exemplos:
      | ph   |
      | -3.2 |
      | 21.4 |
