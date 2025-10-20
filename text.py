          #and iterate from the start again with the next value..
while True:
    print("who are you")
    name  = input()
    if name != 'Joe':
        continue
    print('Hello, Joe. What is the password? (It is a fish.)')
    password = input()
    if password == 'password':
        break
print("Access granted")

###############
num = 0
for i in range(2):
    print(f'number what again: {i}')
    data = i
    print(f'value: {data}')
    for data in range(100):
        print(f'whats: {i}')
        print(f'whats the total num: {int(i + num)}\n')