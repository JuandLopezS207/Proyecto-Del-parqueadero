import users  # Importa el módulo de usuarios

def test_registeruser():
    # Datos de prueba
    id = 1234556
    contraseña = "456723"
    programa = "matematicas"
    rol = "estudiante"
        # Llama a la función para registrar un usuario
    resultado = users.registerUser(id, contraseña, programa, rol)
    # Verifica que el resultado sea el esperado
    assert resultado == "Usuario registrado exitosamente", f"Se esperaba 'Usuario registrado exitosamente', pero se obtuvo '{resultado}'"

def test_getQR():
    # datos de prueba
    id = 1234556
    contraseña = "456723"
    programa = "matematicas"
    rol = "estudiante"
    #llama la funcion
    resultado = users.getQR(id, contraseña, programa, rol)
    # Verifica que el resultado sea del tipo bytes ya que nos si vemos el codigo original el buffer nos esta devolviendo los bits de la imagen 
    assert type(resultado)is bytes, "Se esperaba que el resultado fuera del tipo bytes"


def test_sendQR():
    #los datos de prueba 
    id = 1234556
    contraseña = "456723"
    programa = "matematicas"
    rol = "estudiante"
    
    # Llama a la función para enviar el código QR
    resultado = users.sendQR(id, contraseña, programa, rol)
    # Verifica que el resultado sea el esperado
    assert resultado == "Código QR enviado exitosamente", f"Se esperaba 'Código QR enviado exitosamente', pero se obtuvo '{resultado}'"