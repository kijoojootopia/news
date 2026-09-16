import random

def generate_lotto_numbers():
    # 1부터 45까지의 숫자 중 중복 없이 6개를 추출 후 오름차순 정렬
    return sorted(random.sample(range(1, 46), 6))

if __name__ == "__main__":
    print(f"추출된 번호: {generate_lotto_numbers()}")


# 테스트 하는 중
# test-1
# test-2
#dlfjsdklfjaslkdfjsklfjlskdfjl
# 이제 진짜 진짜 마지막
# 진짜 마지막