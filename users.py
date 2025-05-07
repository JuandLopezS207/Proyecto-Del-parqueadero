from pyzbar.pyzbar import decode
from PIL import Image
from json import dumps, loads
from hashlib import sha256
from Crypto.Cipher import AES
import base64
import pyqrcode
from os import urandom
import io
from datetime import datetime
import cv2
import numpy as np

# se lee el archivo de usuarios, si no existe se crea uno nuevo
usersFileName = "users.txt"
try:
    #intenta abrir el archivo en modo lectura, si no existe lo crea
    archivo = open(usersFileName, "x")
    # se cierra el archivo para evitar errores porque puede que no se haya creado
    archivo.close()
except:
    pass
#verifica cual es el color predominante en la imagen
def color_predominante(region):
    promedio_b = np.mean(region[:, :, 0])
    promedio_g = np.mean(region[:, :, 1])
    promedio_r = np.mean(region[:, :, 2])
    
    if promedio_b > promedio_g and promedio_b > promedio_r:
        return "B", (255, 0, 0)
    elif promedio_g > promedio_b and promedio_g > promedio_r:
        return "G", (0, 255, 0)
    elif promedio_r > promedio_b and promedio_r > promedio_g:
        return "R", (0, 0, 255)
    else:
        return "Indefinido", (255, 255, 255)
#analisa si la zona es libre o ocupada, si es libre devuelve el color blanco y si no el color predominante
def analisis_zona(zona):
    gris = cv2.cvtColor(zona, cv2.COLOR_BGR2GRAY)
    bordes = cv2.Canny(gris, 100, 200)
    porcentaje_bordes = np.count_nonzero(bordes) / bordes.size
    #si esta libre el porcentaje de bordes es menor al 5%
    if porcentaje_bordes < 0.05:
        return "Free", (255, 255, 255)
    #si no esta libre se analiza el color predominante
    else:
        color, colorrec = color_predominante(zona)
        return f"set ({color})", colorrec
#el parqueadero tiene 13 puesto 5 para profesores y 8 para estudiantes
#aca se definen donde se ubican llevada a escala de pixeles 
puestos = [
    (100, 100, 167, 196), (167, 100, 234, 196), (234, 100, 301, 196),
    (301, 100, 368, 196), (368, 100, 435, 196),
    (100, 229, 167, 325), (167, 229, 234, 325), (234, 229, 301, 325), (301, 229, 368, 325),
    (100, 325, 167, 421), (167, 325, 234, 421), (234, 325, 301, 421), (301, 325, 368, 421),
]

date = None
key = None

def encrypt_AES_GCM(msg, secretKey):
    aesCipher = AES.new(secretKey, AES.MODE_GCM)
    ciphertext, authTag = aesCipher.encrypt_and_digest(msg)
    return (ciphertext, aesCipher.nonce, authTag)

def decrypt_AES_GCM(encryptedMsg, secretKey):
    (ciphertext, nonce, authTag) = encryptedMsg
    aesCipher = AES.new(secretKey, AES.MODE_GCM, nonce)
    plaintext = aesCipher.decrypt_and_verify(ciphertext, authTag)
    return plaintext

def generateQR(id, program, role, buffer):
    global key, date
    data = {'id': id, 'program': program, 'role': role}
    datas = dumps(data).encode("utf-8")

    if key is None or date != datetime.today().strftime('%Y-%m-%d'):
        key = urandom(32)
        date = datetime.today().strftime('%Y-%m-%d')

    encrypted = list(encrypt_AES_GCM(datas, key))
    qr_text = dumps({
        'qr_text0': base64.b64encode(encrypted[0]).decode('ascii'),
        'qr_text1': base64.b64encode(encrypted[1]).decode('ascii'),
        'qr_text2': base64.b64encode(encrypted[2]).decode('ascii')
    })

    qrcode = pyqrcode.create(qr_text)
    qrcode.png(buffer, scale=8)
    buffer.seek(0)
    return buffer

def registerUser(id, password, program, role):
    #abre el archivo en modo lectura y guarda los usuarios en una lista
    archivo = open(usersFileName, "r")
    #guarda los usuarios en una lista
    users = archivo.readlines()
    archivo.close()
    #recorre la lista de usuarios y verifica si el id ya existe
    for user in users:
        #se usa para separar el id, la contraseña y el programa
        #donde le quita espacios en blanco y separa por comas
        partes = user.strip().split()
        #si no hay partes se continua con el siguiente usuario
        if len(partes) == 0:
            continue
        if partes[0] == str(id):
            return "User already registered"
    # si se llega a este punto es porque el id no existe
    #va a abrir el archivo en un modo que permita expandir el archivo y agregarle al final un nuevo usuario
    archivo = open(usersFileName, "a")
    #va a sobreescribir el archivo y agregarle el nuevo usuario
    archivo.write(f"{id} {password} {program} {role}\n")
    archivo.close()
    return "User succesfully registered"

def getQR(id, password):
    #va a leer el archivo en modo lectura y guardar los usuarios en una lista
    archivo = open(usersFileName, "r")
    #guarda los usuarios en una lista
    users = archivo.readlines()
    archivo.close()
    buffer = io.BytesIO() 
    #recorre la lista de usuarios y verifica si el id y la contraseña son correctos
    for user in users:
        partes = user.strip().split()
        if partes[0] == str(id) and partes[1] == password:
            buffer = io.BytesIO()
            return generateQR(id, partes[2], partes[3], buffer)
    
    return "Usuario no registrado"

def sendQR(png):
    global key
    # Verifica si el qr es valido o no, ya que al no ser valido pues dara error por lo cual se maneja ese error
    try:
        decodedQR = decode(Image.open(io.BytesIO(png)))[0].data.decode('ascii')
        data = loads(decodedQR)

        decrypted = loads(decrypt_AES_GCM((
            base64.b64decode(data["qr_text0"]),
            base64.b64decode(data["qr_text1"]),
            base64.b64decode(data["qr_text2"])
        ), key))
        # abre el archivo en modo lectura y guarda los usuarios en una lista
        archivo = open(usersFileName, "r")
        users = archivo.readlines()
        archivo.close()
        #verifica si el id y la contraseña son correctos
        encontrado = False
        for user in users:
            partes = user.strip().split()
            if partes[0] == str(decrypted["id"]):
                encontrado = True
        if not encontrado:
            return "Error, el usuario no se encuentra registrado"

        # abre la camara y toma una foto
        video = cv2.VideoCapture("https://192.168.1.118:808/video")
        ret, frame = video.read()
        video.release()
        # si no se puede leer la camara, se devuelve un frame blanco
        if not ret:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)  # blanco
        #una lista que va a guardas los puestos libres  que se pueden asignar
        puestos_libres = []
        #recorre los puestos y analiza cada uno de ellos donde si las cooordenadas son separadas por comas y se asignan a las variables px1, py1, px2 y py2
        #donde se analiza la zona y se guarda el resultado en la variable texto
        for i, (px1, py1, px2, py2) in enumerate(puestos):
            zona = frame[py1:py2, px1:px2]
            texto, _ = analisis_zona(zona)
            if texto == "Free":
                puestos_libres.append(i + 1)
        #se le asigna un puesto deacuerdo al rol del usuario
        if decrypted["role"] == "profesor":
            rango = range(0, 5)
        elif decrypted["role"] == "estudiante":
            rango = range(5, len(puestos))
        
        else:
            return "Error, el rol no es valido"
        #se muestra ell puesto asignado
        for i in rango:
            if (i + 1) in puestos_libres:
                return f"Puesto asignado: {i + 1}"

        return "No hay puestos disponibles para su rol"

    except:
       return "Error, la clave ha expirado o el QR no es valido"
    

