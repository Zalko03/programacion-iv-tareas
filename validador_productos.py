import json

def validar_datos(nombre_archivo):
    # Valida un archivo JSON verificando formato correcto y tipos numéricos.
    try:
        with open(nombre_archivo, 'r', encoding='utf-8') as archivo_json:
            datos = json.load(archivo_json)  # Intenta cargar el contenido del archivo JSON en la variable 'datos'

            # Comprueba que el contenido raíz sea una lista
            if not isinstance(datos, list):
                raise ValueError("El contenido del archivo JSON no es una lista.")  # Lanza un error si el contenido no es una lista

            # Recorre cada elemento verificando que el precio sea entero.
            for item in datos:
                if not isinstance(item.get('precio'), int):
                    raise TypeError("El precio de un producto no es un número entero.")  # Lanza un error si el precio no es un entero

            print("Validación exitosa: El archivo JSON tiene el formato correcto y los precios son números enteros.")  # Mensaje de éxito si todo es correcto
            return datos  # Retorna los datos validados si no hay errores

    except FileNotFoundError:
        print(f"Error: El archivo '{nombre_archivo}' no se encontró.")  # Mensaje de error si el archivo no existe
        return None  # Retorna None para indicar que no se pudo validar el archivo

    except json.JSONDecodeError:
        print(f"Error: El archivo '{nombre_archivo}' no tiene un formato JSON válido.")  # Mensaje de error si el archivo no es un JSON válido
        return None  # Retorna None para indicar que no se pudo validar el archivo

    except (ValueError, TypeError) as e:
        print(f"Error: en la validación de datos: {e}")  # Mensaje de error si hay un problema con los tipos de datos
        return None  # Retorna None para indicar que no se pudo validar el archivo