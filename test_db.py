import traceback
import sys

try:
    from database import Database
    db = Database()
    print('Success')
except Exception as e:
    with open('tb2.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
