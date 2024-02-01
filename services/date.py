import arrow
from loguru import logger


def to_unix_timestamp(date_str: str) -> int:
    """
    날짜 문자열을 Unix 타임스탬프(에포크 이후 초)로 변환

    Args:
        date_str: 변환할 날짜 문자열
    return:
        날짜 문자열에 해당하는 Unix 타임스탬프
    날짜 문자열을 유효한 날짜 형식으로 파싱할 수 없는 경우 현재 Unix 타임스탬프를 반환하고 경고를 출력
    """
    try:
        date_obj = arrow.get(date_str)
        return int(date_obj.timestamp())
    except arrow.parser.ParserError:
        # 구문 분석에 실패하면 현재 Unix 타임스탬프를 반환하고 경고를 출력합니다.
        logger.info(f"Invalid date format: {date_str}")
        return int(arrow.now().timestamp())
