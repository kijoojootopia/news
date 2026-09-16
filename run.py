"""VS Code terminal: python run.py"""
# 안녕
import os
from getpass import getpass
from app import create_app

# 아 진짜 귀엽다 고양이 미쳣당
def main():
    try:
        api_key = getpass("OpenAI API 키를 입력하세요 (Enter: 데모 모드): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n실행을 취소했습니다.")
        return

    app = create_app({
        "OPENAI_API_KEY": api_key,
        "AI_MODE": "openai" if api_key else "demo",
    })
    print("AI 모드로 시작합니다." if api_key else "데모 모드로 시작합니다.")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)


if __name__ == "__main__":
    main()
