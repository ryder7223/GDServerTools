import pymem
import pymem.process

def readMemory(processName, baseOffset, offsets, derefMask, dataType="string", length=32):
    try:
        pm = pymem.Pymem(processName)
    except pymem.exception.ProcessNotFound:
        print("Process not open.")
        return
    module = pymem.process.module_from_name(pm.process_handle, processName)
    baseAddress = module.lpBaseOfDll

    currentAddress = baseAddress + baseOffset

    # Initial deref (almost always needed)
    currentAddress = pm.read_longlong(currentAddress)

    for i, offset in enumerate(offsets):
        currentAddress += offset

        # Only deref if mask says so
        if derefMask[i]:
            currentAddress = pm.read_longlong(currentAddress)

    finalAddress = currentAddress

    #print(f"Base Address: 0x{baseAddress:X}")
    #print(f"Final Address: 0x{finalAddress:X}")

    if dataType == "int":
        return pm.read_int(finalAddress)

    elif dataType == "uint":
        return pm.read_uint(finalAddress)

    elif dataType == "float":
        return pm.read_float(finalAddress)

    elif dataType == "double":
        return pm.read_double(finalAddress)

    elif dataType == "longlong":
        return pm.read_longlong(finalAddress)

    elif dataType == "bytes":
        return pm.read_bytes(finalAddress, length)

    elif dataType == "string":
        rawBytes = pm.read_bytes(finalAddress, length)
        return rawBytes.split(b'\x00', 1)[0].decode(errors="ignore")

    else:
        raise ValueError("Unsupported data type")

GJP2 = readMemory(
    "GeometryDash.exe",
    0x6C2EF0,
    offsets=[0x178, 0x0],
    derefMask=[True, False],
    dataType="string",
    length=40
)

print(f"Value: {GJP2}")
