# Es = a comentario, NO USAR //

#Lista de diccionarios
import csv    #Se agregan librerías con el comando import, en este caso se importa la librería csv para poder leer archivos CSV.
import json  #Se importa la librería json para poder trabajar con datos en formato JSON.
from validador_productos import validar_datos # Se importa la función 'validar_datos' desde el módulo 'validador_productos.py' para poder usarla en este archivo.


# productos = [
#     {"nombre": "Laptop", "precio": 1200, "stock": 15}, 
#     {"nombre": "Mouse", "precio": 25, "stock": 5},
#     {"nombre": "Teclado", "precio": 75, "stock": 25},
#     {"nombre": "Monito", "precio": 300, "stock": 8},
# ]
    
# print (productos[1] ["nombre"]) #Esto imprimirá "Mouse" ya que accede al segundo diccionario en la lista (índice 1) y luego obtiene el valor asociado a la clave "nombre".
# print (productos[2] ["precio"]) #Esto imprimirá 75 ya que accede al tercer diccionario en la lista (índice 2) y luego obtiene el valor asociado a la clave "precio".
# print (productos[3] ["stock"]) #Esto imprimirá 8 ya que accede al cuarto diccionario en la lista (índice 3) y luego obtiene el valor asociado a la clave "stock".

# # Inicializa una lista vacía para guardar los elementos que cumplan la condición de stock
# productos_bajo_stock = []  
# # Recorre cada diccionario dentro de la lista 'productos' usando la variable 'producto' 
# for producto in productos: 
#     # Muestra por consola el nombre y precio del producto actual mediante f-string
#     print(f"Producto: {producto['nombre']}, Precio: ${producto['precio']}")

#     ## Evalúa si la cantidad de stock del producto actual es estrictamente menor a 10
#     if producto["stock"] < 10: 
#         # Añade el diccionario completo del producto al final de la lista de bajo stock
#         productos_bajo_stock.append(producto)

# # Imprime un salto de línea inicial (\n) seguido del mensaje de advertencia
# print("\nProductos con bajo Stock, procura llenarlos")
# # Muestra en consola la lista resultante con los productos filtrados
# print(productos_bajo_stock)


## Define la función 'calcular_promedio_precio' que recibe como parámetro una lista
# def calcular_promedio_precio(lista): 
#     if not lista: # Define la función 'calcular_promedio_precio' que recibe como parámetro una lista
#         return 0 # Retorna 0 de inmediato para evitar un error de división por cero
#     total_precio = sum(p['precio'] for p in lista) # Recorre cada elemento 'p', extrae su clave 'precio' y suma todos los valores acumulados

#     return total_precio / len(lista)  # Divide la suma acumulada por la cantidad total de elementos y devuelve el promedio

# ## Invoca a la función enviándole la lista 'productos' y guarda el promedio retornado
# precio_promedio = calcular_promedio_precio(productos) 

# # Imprime un salto de línea inicial (\n) y muestra el valor con exactamente dos decimales (:.2f)
# print(f"\nEl precio promedio de los productos es: ${precio_promedio:.2f}")



# def validar_datos(nombre_archivo):
#        #Valida un archivo JSON verificando formato correcto y tipos numéricos.
#     try:
#           with open(nombre_archivo, 'r', encoding='utf-8') as archivo_json:
#                 datos = json.load(archivo_json)  # Intenta cargar el contenido del archivo JSON en la variable 'datos'

#                 # Comprueba que el contenido raíz sea una lista
#                 if not isinstance(datos, list):
#                       raise ValueError("El contenido del archivo JSON no es una lista.")  # Lanza un error si el contenido no es una lista

#                 # Recorre cada elemento verificando que el precio sea entero.
#                 for item in datos:
#                       if not isinstance(item.get('precio'), int):
#                             raise ValueError("El precio de un producto no es un número entero.")  # Lanza un error si el precio no es un entero

#                       print("Validación exitosa: El archivo JSON tiene el formato correcto y los precios son números enteros.")  # Mensaje de éxito si todo es correcto
#                       return datos # Retorna los datos validados si no hay errores

#     except FileNotFoundError:
#                     print(f"Error: El archivo '{nombre_archivo}' no se encontró.")  # Mensaje de error si el archivo no existe
#                     return None  # Retorna None para indicar que no se pudo validar el archivo
          
#     except json.JSONDecodeError:
#                     print(f"Error: El archivo '{nombre_archivo}' no tiene un formato JSON válido.")  # Mensaje de error si el archivo no es un JSON válido
#                     return None  # Retorna None para indicar que no se pudo validar el archivo

#     except (ValueError, TypeError) as e:
#                     print(f"Error: en la validación de datos: {e}")  # Mensaje de error si hay un problema con los tipos de datos

                
productos_desde_csv =[]

with open ('datos.csv', mode='r', encoding='utf-8') as archivo_csv:
    lector_diccionario = csv.DictReader(archivo_csv)
    for fila in lector_diccionario: 
        fila['id'] = int(fila['id'])  # Convertir el valor de 'id' a entero
        fila['precio'] = int(fila['precio'])  # Convertir el valor de 'precio' a entero
        fila['stock'] = int(fila['stock'])  # Convertir el valor de 'stock' a entero
        productos_desde_csv.append(fila)  # Agregar el diccionario modificado a la lista

    print("\nLista de productos desde el archivo CSV:")
   # print(productos_desde_csv)

for producto in productos_desde_csv:  # Recorre cada diccionario dentro de la lista 'productos_desde_csv' usando la variable 'producto'
        print(f"Producto: {producto['nombre']}, Precio: ${producto['precio']}, Stock: {producto['stock']}") #Muestra por consola el nombre, precio y stock del producto actual mediante f-string


if productos_desde_csv:
              datos_json = json.dumps(productos_desde_csv, indent=4)  # Convierte la lista de diccionarios a una cadena JSON con una sangría de 4 espacios para mejorar la legibilidad.
              with open('salida.json', 'w', encoding='utf-8') as archivo_json: # Abre (o crea) un archivo llamado 'salida.json' en modo escritura ('w') con codificación UTF-8.
                  archivo_json.write(datos_json)  # Escribe la cadena JSON en el archivo.



print("\n--- Ejecutando el validador ---")
# validar_datos('salida.json')
datos_validados = validar_datos('salida.json')  # Llama a la función 'validar_datos' pasando el nombre del archivo JSON como argumento y guarda el resultado en 'datos_validados'
if datos_validados is not None:  # Verifica si la validación fue exitosa (es decir, si 'datos_validados' no es None)
    print("Datos validados correctamente. Aquí están los datos:")
    print(datos_validados)  # Muestra los datos validados en la consola