import random
import json

ZODIAC_FORTUNES = {
    "양자리": "새로운 시도가 뜻밖의 영감을 가져다주는 날입니다.",
    "황소자리": "차분한 쉼표 속에서 하루의 따뜻한 여유를 만끽할 수 있습니다.",
    "쌍둥이자리": "다양한 대화 속에서 반짝이는 아이디어를 얻게 됩니다.",
    "게자리": "마음이 편안해지는 아늑한 순간이 기다리고 있습니다.",
    "사자자리": "당신의 당당한 매력이 주변을 화사하게 밝힙니다.",
    "처녀자리": "정돈된 일상에서 소소하지만 확실한 만족을 찾습니다.",
    "천칭자리": "조화로운 리듬 속에서 기분 좋은 만남이 기대됩니다.",
    "전갈자리": "깊이 몰입했던 일에서 기대 이상의 보람을 느낍니다.",
    "사수자리": "발걸음 닿는 곳마다 즐거운 모험과 발견이 따릅니다.",
    "염소자리": "꾸준히 쌓아 올린 시간들이 빛을 발하기 시작합니다.",
    "물병자리": "틀을 깨는 나만의 감각이 특별한 하루를 완성합니다.",
    "물고기자리": "따스한 상상력이 메마른 일상을 촉촉하게 적셔줍니다."
}

FORTUNE_COOKIES = [
    "작은 용기가 커다란 행운의 문을 엽니다.",
    "오늘 당신이 들은 음악 한 곡이 오랫동안 마음에 남을 것입니다.",
    "기대하지 않았던 골목에서 당신만의 명장면을 마주하게 됩니다.",
    "따뜻한 차 한 잔으로 마음의 온도를 1도 올려보세요.",
    "오늘 찍은 사진 속 미소는 가장 소중한 부적이 됩니다."
]

def generate_newspaper_articles(nickname, highlight_entry, other_entries, include_horoscope, zodiac_sign, include_fortune):
    # LLM API 확장을 고려한 Structured Mock Engine
    main_title = f"{nickname}의 특별한 하루, 역사에 기록되다"
    main_body = f"{nickname}은(는) 오늘 가장 인상 깊은 순간으로 다음을 꼽았다: '{highlight_entry.content if highlight_entry else '평온한 일상의 흐름'}'."
    
    gossip = f"취재진에 따르면 {nickname}은(는) 오늘 유난히 기분 좋은 에너지를 풍기며 주변의 이목을 집중시켰다는 후문이다."
    
    music_data = None
    records = []
    for e in other_entries:
        if e.topic == 'music':
            extra = e.get_extra()
            music_data = {
                "title": extra.get("title", "Unknown Title"),
                "artist": extra.get("artist", "Unknown Artist"),
                "comment": e.content
            }
        else:
            records.append({
                "topic": e.topic,
                "content": e.content,
                "image": e.image_path
            })
            
    horoscope_text = ZODIAC_FORTUNES.get(zodiac_sign, "오늘 하루도 반짝이는 빛이 함께합니다.") if include_horoscope else None
    fortune_text = random.choice(FORTUNE_COOKIES) if include_fortune else None

    return {
        "headline": main_title,
        "main_article": main_body,
        "gossip": gossip,
        "music": music_data,
        "records": records,
        "horoscope": horoscope_text,
        "fortune": fortune_text
    }