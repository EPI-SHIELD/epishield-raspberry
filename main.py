import cv2
import os
import time
from dotenv import load_dotenv
from gpiozero import OutputDevice
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis do arquivo .env
load_dotenv()

# Configurações do ambiente
MODEL_PATH = os.getenv("MODEL_PATH", "./modelo.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 17))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.8))
TARGET_LABEL = os.getenv("TARGET_LABEL", "autorizado")
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# Inicializa o pino da catraca
# Ajuste active_high para False se o seu módulo relé for ativado em nível baixo (GND)
catraca = OutputDevice(GPIO_PIN, active_high=True, initial_value=False)

def abrir_catraca():
    print("Acesso liberado. Abrindo catraca...")
    catraca.on()
    time.sleep(OPEN_TIME)
    catraca.off()
    print("Catraca fechada.")

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        
        # Loop de inferência contínua usando a câmera
        for res, img in runner.classifier(CAMERA_ID):
            
            # Para modelos de Classificação de Imagem
            if "classification" in res["result"]:
                predictions = res["result"]["classification"]
                if TARGET_LABEL in predictions and predictions[TARGET_LABEL] >= THRESHOLD:
                    print(f"Confiança ({TARGET_LABEL}): {predictions[TARGET_LABEL]:.2f}")
                    abrir_catraca()
                    time.sleep(1) # Delay de segurança
                    
            # Para modelos de Detecção de Objetos (Bounding Boxes)
            elif "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    if bb["label"] == TARGET_LABEL and bb["value"] >= THRESHOLD:
                        print(f"Confiança ({bb['label']}): {bb['value']:.2f}")
                        abrir_catraca()
                        time.sleep(1)

    finally:
        if runner:
            runner.stop()

if __name__ == "__main__":
    main()