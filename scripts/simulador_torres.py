"""Simula uma ou mais torres no broker, com os topicos novos.

Uso:
    export MQTT_USER=... MQTT_PASS=...
    python scripts/simulador_torres.py --torre AT-5130AA000001:pro --torre AT-5130AA000002:basico

Cada torre:
  * publica aerotower/<id>/status (online, retido) e deixa o LWT "offline";
  * publica aerotower/<id>/info com firmware, kit e sensores;
  * publica aerotower/<id>/sensores a cada 5 s, SO com os sensores do kit,
    com valores que variam devagar (sem saltos);
  * obedece aerotower/<id>/motor/comando (ciclo/desligar) e responde em
    motor/status, como o ESP32.
O reservatorio esvazia com a bomba ligada e e reabastecido ao chegar a
20%, para o alerta de nivel baixo aparecer sozinho numa demonstracao.

Para a torre aparecer no app, cadastre-a antes com
scripts/provisionar_torre.py --torre-id <id> --kit <kit>.
"""
import argparse
import json
import os
import random
import ssl
import time

import paho.mqtt.client as mqtt

BROKER  = os.getenv("MQTT_BROKER", "47d5de0ce14d4654a95021e273720719.s1.eu.hivemq.cloud")
PORTA   = int(os.getenv("MQTT_PORT", "8883"))
PREFIXO = os.getenv("MQTT_PREFIXO", "aerotower")
USAR_TLS = os.getenv("MQTT_TLS", "true").lower() != "false"   # false so p/ broker local
SENSORES_POR_KIT = {"basico": [], "completo": ["nivel"], "pro": ["nivel", "ph", "tds", "clima"]}


class TorreSimulada:
    def __init__(self, torre_id: str, kit: str):
        self.id, self.kit = torre_id, kit
        self.base = f"{PREFIXO}/{torre_id}"
        self.ph, self.tds, self.temp, self.umid, self.nivel = 6.0, 700.0, 24.0, 60.0, 80.0
        self.motor, self.ciclo, self.lig, self.des, self.mudou = True, True, 15, 45, time.time()

        try:  # paho-mqtt 2.x
            self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=torre_id)
        except AttributeError:  # paho-mqtt 1.x
            self.cliente = mqtt.Client(client_id=torre_id)
        self.cliente.username_pw_set(os.getenv("MQTT_USER", ""), os.getenv("MQTT_PASS", ""))
        if USAR_TLS:
            self.cliente.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.cliente.will_set(f"{self.base}/status", json.dumps({"status": "offline"}), qos=1, retain=True)
        self.cliente.on_connect = self._conectou
        self.cliente.on_message = self._comando

    def iniciar(self):
        self.cliente.connect(BROKER, PORTA, 30)
        self.cliente.loop_start()

    def _conectou(self, cliente, *_):
        print(f"[{self.id}] conectado")
        cliente.publish(f"{self.base}/status", json.dumps({"status": "online"}), qos=1, retain=True)
        cliente.publish(f"{self.base}/info", json.dumps({
            "firmware": "sim-2.0.0", "kit": self.kit, "sensores": SENSORES_POR_KIT[self.kit],
        }), qos=1, retain=True)
        cliente.subscribe(f"{self.base}/motor/comando", qos=1)
        self._status_motor()

    def _comando(self, cliente, userdata, msg):
        dados = json.loads(msg.payload or b"{}")
        print(f"[{self.id}] comando {dados}")
        if dados.get("acao") == "ciclo":
            self.lig, self.des = dados.get("minutos_ligado", 15), dados.get("minutos_desligado", 45)
            self.ciclo, self.motor, self.mudou = True, True, time.time()
        elif dados.get("acao") == "desligar":
            self.ciclo, self.motor = False, False
        self._status_motor()

    def _status_motor(self):
        self.cliente.publish(f"{self.base}/motor/status", json.dumps({
            "ligado": self.motor, "ciclo_ativo": self.ciclo,
            "minutos_ligado": self.lig, "minutos_desligado": self.des,
        }), qos=1, retain=True)

    @staticmethod
    def _passo(valor, alvo, ruido, minimo, maximo):
        valor += (alvo - valor) * 0.05 + random.uniform(-ruido, ruido)
        return max(minimo, min(maximo, valor))

    def publicar(self):
        if self.ciclo and time.time() - self.mudou > (self.lig if self.motor else self.des) * 60:
            self.motor, self.mudou = not self.motor, time.time()
            self._status_motor()

        dados = {"motor": self.motor, "ciclo_ativo": self.ciclo}
        sensores = SENSORES_POR_KIT[self.kit]
        if "nivel" in sensores:
            self.nivel -= 0.6 if self.motor else 0.1
            if self.nivel < 20:
                self.nivel = 95.0   # "reabasteceu"
            dados.update(nivelAgua=round(self.nivel, 1), tanque_litros=round(self.nivel / 5, 2),
                         tanque_status="baixo" if self.nivel < 35 else "ok")
        if "ph" in sensores:
            self.ph = self._passo(self.ph, 6.0, 0.05, 4.5, 8.0)
            dados["ph"] = round(self.ph, 2)
        if "tds" in sensores:
            self.tds = self._passo(self.tds, 700, 15, 100, 1500)
            dados.update(tds=round(self.tds), ec=round(self.tds / 500, 2))
        if "clima" in sensores:
            self.temp = self._passo(self.temp, 24, 0.2, 15, 35)
            self.umid = self._passo(self.umid, 60, 1, 30, 95)
            dados.update(temperaturaAmbiente=round(self.temp, 1), umidadeRelativa=round(self.umid))
        self.cliente.publish(f"{self.base}/sensores", json.dumps(dados))
        print(f"[{self.id}] {dados}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--torre", action="append", required=True, metavar="ID:KIT",
                        help="ex.: AT-5130AA000001:pro (repita para várias)")
    parser.add_argument("--intervalo", type=float, default=5.0)
    args = parser.parse_args()

    torres = []
    for item in args.torre:
        torre_id, _, kit = item.partition(":")
        torres.append(TorreSimulada(torre_id.upper(), kit or "pro"))
    for torre in torres:
        torre.iniciar()

    try:
        while True:
            time.sleep(args.intervalo)
            for torre in torres:
                torre.publicar()
    except KeyboardInterrupt:
        for torre in torres:
            torre.cliente.publish(f"{torre.base}/status", json.dumps({"status": "offline"}), retain=True)
            torre.cliente.loop_stop()
            torre.cliente.disconnect()


if __name__ == "__main__":
    main()
