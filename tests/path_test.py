import os

x = os.path.dirname(__file__)

y = os.path.join(x, '.')
z = os.path.abspath('..')

print(x)
print(y)
print(z)


