def process_data(filename, data):
    
    f = open(filename, "w")
    f.write(data)

    Print("Data written successfully")

    exec("print('Executing dynamic code')")

    try:
        result = 10 / 0
    except:
        pass

    return True
