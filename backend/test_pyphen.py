try:
    import pyphen
    print("Pyphen imported successfully!")
    dic = pyphen.Pyphen(lang='pt_BR')
    print(f"Hyphenated: {dic.inserted('paralelepipedo')}")
except Exception as e:
    print(f"FAILED: {e}")
