ONE = 1
TWO = 2

tokens = {
        '1': ONE,
        '2': TWO
    }
chek_tokens = []
for key, value in tokens.items():
    if value is True:
        chek_tokens.append(key)
print(chek_tokens)

#tokens = (('1', ONE), ('2', TWO),)
#chek_tokens = []
#for token in tokens:
#    for key, value in token:
#        if value == ONE:
#            chek_tokens.append(key)
#print(chek_tokens)