import time

def timer() -> None:
    for minute in range(0, 3):
        for second in range(0, 60):
            print(f'\r   {minute:02d}:{second:02d}', end='')
            time.sleep(1)

            if minute == 2 and second == 0:
                break