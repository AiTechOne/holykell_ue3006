import pymodbus
from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU modbus_client instance
import logging
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
import time


# Logger obj of module
logger = logging.getLogger(__name__)
# logger = logging.getLogger()
logger.setLevel(logging.INFO)

def request(reg, num, modbus_id):
    distance = None
    logger.debug("Measuring distance...")
    try:
        modbus_client = ModbusClient(method="rtu", port=PORT, stopbits=1, bytesize=8, parity="N", baudrate=9600, timeout=0.1)
        if modbus_client.connect():
            height_query = modbus_client.read_holding_registers(reg, count=num, unit=modbus_id)
            distance = BinaryPayloadDecoder.fromRegisters(height_query.registers, byteorder=Endian.Big, wordorder=Endian.Big)
            distance = distance.decode_32bit_float()
            modbus_client.close()
        else:
            logger.error(f'Could not connecto to {PORT} port')
    except Exception as ex:
        logger.error('Error trying to read rs485 sensor')
    return height_query.registers, distance

def read_security_register(modbus_client, modbus_id):
    # 1. Leer registro de bloqueo:
    try:
        read_block_register = modbus_client.read_holding_registers(32790, count=2, unit=modbus_id)
        value_block_register = BinaryPayloadDecoder.fromRegisters(
            read_block_register.registers, 
            byteorder=Endian.Big, 
            wordorder=Endian.Big).decode_32bit_float()
        if value_block_register == 0.0:
            logger.debug("Bloqueo activado!")
            return "lock"
        elif value_block_register == 1.0:
            logger.debug("Bloqueo desactivado!")
            return "unlock"
        else:
            logger.critical(f"FATAL ERROR value_block_register = {value_block_register}")
            return None
    except Exception as ex:
        logger.debug(ex)
    return None

def unlock_security_block(modbus_client, modbus_id):
    # 2. Cambiar valor block register a 1:
    # 2.1 Preparar payload         
    builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
    builder.add_32bit_float(1.0)
    payload = builder.to_registers()
    logger.info(f"Payload 1 (bloque de seguridad = 0.0) preparado: {payload}")

    # 2.2. Escribir registro block:
    result  = modbus_client.write_registers(32790, payload, unit=modbus_id)
    logger.debug(f"Fue un error? {result.isError()}")
    if result.isError():
        return False
    else:
        return True

def lock_security_block(modbus_client, modbus_id):
    # 4. Cambiar valor block register a 0:
    # 4.1 Preparar payload         
    builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
    builder.add_32bit_float(0.0)
    payload = builder.to_registers()
    logger.info(f"Payload 3 (bloque de seguridad = 1.0) preparado: {payload}")

    # 4.2. Escribir registro block:
    result  = modbus_client.write_registers(32790, payload, unit=modbus_id)
    logger.debug(f"Fue un error? {result.isError()}")
    if result.isError():
        return False
    else:
        return True

def read_modbus_id_register(modbus_client, modbus_id):
    # 1. Leer registro de bloqueo:
    read_modbus_id = None
    try:
        result = modbus_client.read_holding_registers(32782, count=2, unit=modbus_id)
        read_modbus_id = BinaryPayloadDecoder.fromRegisters(
            result.registers, 
            byteorder=Endian.Big, 
            wordorder=Endian.Big).decode_32bit_float()
    except Exception as ex:
        logger.debug(ex)
    if read_modbus_id == modbus_id:
        return True
    else:
        logger.debug(f"Modbus ID = {read_modbus_id} not {modbus_id}!!!")
        return False

def update_modbus_id(modbus_client, modbus_id, new_id):
    # 3. Cambiar modbus ID:
    # 3.1 Preparar payload        
    try: 
        builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
        builder.add_32bit_float(new_id)
        payload = builder.to_registers()
        logger.debug(f"Payload 2 (nuevo modbusID={new_id}) preparado: {payload}")

        # 3.2. Escribir registro block:
        result  = modbus_client.write_registers(32782, payload, unit=modbus_id)
    except Exception as ex:
        logger.debug(ex)
    return True

def measure(modbus_client, modbus_id):
    # 5 Medicion de prueba:
    for i in range(5):
        height_query = modbus_client.read_holding_registers(0, count=2, unit=modbus_id)
        if height_query.isError():
            continue
        else:
            break
    distance = BinaryPayloadDecoder.fromRegisters(height_query.registers, byteorder=Endian.Big, wordorder=Endian.Big)
    distance = distance.decode_32bit_float() * 100
    logger.info(f"Distancia medida = {distance}")
    return distance


def search_sensor_modbus_id(modbus_client):
    for m_id in range(255):
        if read_modbus_id_register(modbus_client, modbus_id=m_id):
            break
    logger.info(f"Sensor found on Modbus ID = {m_id}")
    return m_id

def holykell_update_modbus_id():
    n = 10
    t_sleep = .1

    logger.info("####################################################################")
    logger.info("#                    Upgrade Hollykell Modbus ID                   #")
    logger.info("####################################################################\n")
    PORT = input("Port? (/dev/<something> or COM<number>): ")
    modbus_client = ModbusClient(method="rtu", port=PORT, stopbits=1, bytesize=8, parity="N", baudrate=9600, timeout=0.1)
    MODBUS_ID = input("Current Modbus ID (0-255 or empty if unknown)?: ")
    if MODBUS_ID is "":
        MODBUS_ID = search_sensor_modbus_id(modbus_client)
    NEW_MODBUS_ID = int(input("New Modbus ID (0-255)?: "))
    confirm = input(f"\n\nConfirm:\n\tPort={PORT}\n\tCurrent Modbus ID={MODBUS_ID}\n\tNew Modbus ID={NEW_MODBUS_ID}\nOk? (y/n): ")
    if confirm.lower() == 'y':
        logger.info("")
        logger.info("")
        logging.info("Initializing...")
        try:
            
            if modbus_client.connect():
                logger.info("Completed 0/6")
                for i in range(3):
                    time.sleep(t_sleep)
                    ans = read_modbus_id_register(modbus_client, modbus_id=MODBUS_ID)
                    if ans is True:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 0. Finalizando!")
                    return False

                logger.info("Completed 1/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = read_security_register(modbus_client, modbus_id=MODBUS_ID)
                    if ans:
                        if ans is False:
                            logger.warning("Registro estaba desbloqueado!")
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 1. Finalizando!")
                    return False

                logger.info("Completed 2/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = unlock_security_block(modbus_client, modbus_id=MODBUS_ID)
                    if ans is True:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 2. Finalizando!")
                    return False

                logger.info("Completed 3/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    update_modbus_id(modbus_client, modbus_id=MODBUS_ID, new_id=NEW_MODBUS_ID)
                    ans = read_modbus_id_register(modbus_client, modbus_id=NEW_MODBUS_ID)
                    if ans is True:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 5. Finalizando!")
                    return False
                logger.info(f"\tModbus ID actualizado a {NEW_MODBUS_ID}")

                logger.info("Completed 4/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = lock_security_block(modbus_client, modbus_id=NEW_MODBUS_ID)
                    if ans:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 4. Finalizando!")
                    return False

                logger.info("Completed 5/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = read_security_register(modbus_client, modbus_id=NEW_MODBUS_ID)
                    if ans == 'lock':
                        logger.info("Registro bloqueado exitosamente")
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 5. Finalizando!")
                    return False

                logger.info("Completed 6/6")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = read_modbus_id_register(modbus_client, modbus_id=NEW_MODBUS_ID)
                    if ans is True:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                else:
                    logger.error("Error en etapa 6. Finalizando!")

                logger.info("Reading Distance...")
                for i in range(n):
                    time.sleep(t_sleep)
                    ans = measure(modbus_client, modbus_id=NEW_MODBUS_ID)
                    if ans:
                        break
                    logger.debug(f"Error. Retrying...{i+1}/{n}")
                
                logger.info("Finished! :D")
                modbus_client.close()
            else:
                logger.error(f'Could not connecto to {PORT} port')
        except Exception as ex:
            logger.exception(ex)
            logger.error('Error trying to read rs485 sensor')
    else:
        logger.info("Start again!")
    return True


if __name__ == '__main__':
    formatter = logging.Formatter('%(asctime)s ## %(funcName)s(%(lineno)d-%(levelname)s): %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    holykell_update_modbus_id()

