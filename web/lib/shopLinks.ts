// 쿠팡 파트너스 제휴 링크 — 웹 /shop 페이지 데이터.
// 링크 교체 시 이 파일만 수정 (data/coupang_shortlinks.csv 와 동일 소스, 웹 배포용 사본).
export type ShopLink = {
  category: string;
  url: string;
  hint: string;
  emoji: string;
};

export const SHOP_LINKS: ShopLink[] = [
  { category: "K-POP 굿즈", url: "https://link.coupang.com/a/eGKMNCCA6m", hint: "응원봉 · 앨범 · 포카 · 슬리브", emoji: "💿" },
  { category: "야식 · 치킨", url: "https://link.coupang.com/a/eGKQf4W9zE", hint: "치킨 · 엽떡 · 닭발 · 안주", emoji: "🍗" },
  { category: "홈트 · 요가", url: "https://link.coupang.com/a/eGKUivMJGu", hint: "요가매트 · 홈트 · 덤벨", emoji: "🧘" },
  { category: "캠핑 · 피크닉", url: "https://link.coupang.com/a/eGKVVgheCG", hint: "피크닉 매트 · 캠핑 의자", emoji: "🏕️" },
  { category: "도시락 · 간편식", url: "https://link.coupang.com/a/eGKXG6VzUq", hint: "도시락통 · 직장인 도시락", emoji: "🍱" },
  { category: "여행 · 캐리어", url: "https://link.coupang.com/a/eGK0HhNIjY", hint: "여행 캐리어 28인치", emoji: "🧳" },
];

export const COUPANG_DISCLOSURE =
  "이 페이지의 링크는 쿠팡 파트너스 활동의 일환으로, 이에 따라 일정액의 수수료를 제공받습니다.";
