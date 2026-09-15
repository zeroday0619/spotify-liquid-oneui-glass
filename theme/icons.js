const labels = {
  home: ["home", "홈"],
  search: ["search", "검색", "검색하기"],
  back: ["go back", "back", "뒤로 가기", "뒤로", "뒤로 이동하기"],
  forward: ["go forward", "forward", "앞으로 가기", "앞으로", "앞으로 이동하기"],
  bell: ["what's new", "새 소식", "새로운 소식", "알림"],
  friends: ["friend activity", "listening activity", "친구 활동", "청취 활동"],
  queue: ["queue", "대기열", "재생 대기열", "재생목록"],
  devices: ["connect to a device", "connect to device", "available devices", "기기에 연결", "기기에 연결하기", "기기 연결", "사용 가능한 기기"],
  volume: ["mute", "음소거", "음소거하기"],
  muted: ["unmute", "음소거 해제", "음소거 해제하기"],
  play: ["play", "재생", "재생하기"],
  pause: ["pause", "일시 정지", "일시정지", "일시 정지하기"],
  previous: ["previous", "previous track", "이전", "이전 곡"],
  next: ["next", "next track", "다음", "다음 곡"],
  shuffle: ["shuffle", "enable shuffle", "disable shuffle", "enable smart shuffle", "disable smart shuffle", "셔플", "셔플 켜기", "셔플 끄기", "스마트 셔플 켜기", "스마트 셔플 끄기"],
  repeat: ["repeat", "enable repeat", "disable repeat", "반복", "반복 켜기", "반복 끄기", "반복 활성화하기", "반복 비활성화하기"],
  "repeat-one": ["enable repeat one", "repeat one", "한 곡 반복 켜기", "한 곡 반복"],
  fullscreen: ["full screen", "fullscreen", "enter full screen", "exit full screen", "전체 화면", "전체 화면 종료", "전체 화면으로 전환"],
  miniplayer: ["open miniplayer", "close miniplayer", "miniplayer", "미니플레이어", "미니 플레이어", "미니플레이어 열기", "미니 플레이어 열기"],
  settings: ["settings", "설정", "liquid glass 설정"],
  add: ["add", "create playlist", "추가", "만들기", "플레이리스트에 추가", "플레이리스트 만들기", "save to your liked songs", "좋아요 표시한 곡에 저장"],
  check: ["remove from your liked songs", "좋아요 표시한 곡에서 삭제"],
  more: ["more", "more options", "더 보기", "더 많은 옵션"],
  close: ["close", "닫기"],
  download: ["download", "다운로드", "다운로드하기"],
  lyrics: ["lyrics", "가사"],
  library: ["your library", "내 라이브러리", "내 보관함"],
};
const labelMap = new Map(Object.entries(labels).flatMap(([name, values]) => values.map(value => [value, name])));
const testIds = {
  "control-button-skip-back": "previous",
  "control-button-skip-forward": "next",
  "control-button-shuffle": "shuffle",
  "control-button-queue": "queue",
  "control-button-lyrics": "lyrics",
  "control-button-fullscreen": "fullscreen",
  "top-bar-back-button": "back",
  "top-bar-forward-button": "forward",
};

export function classifyAppleIcon({ label = "", title = "", testId = "" } = {}) {
  const normalize = value => value.trim().replace(/\s+/g, " ").toLowerCase();
  // State-bearing labels take precedence over static control identifiers.
  return labelMap.get(normalize(label)) || labelMap.get(normalize(title)) || testIds[testId] || null;
}

export function installAppleIcons() {
  const selector = 'button, a, [role="button"]';
  const pending = new Set();
  let frame = 0;
  let disposed = false;

  function decorate(control) {
    if (!(control instanceof Element) || !control.isConnected) return;
    const name = classifyAppleIcon({
      label: control.getAttribute("aria-label") || "",
      title: control.getAttribute("title") || "",
      testId: control.getAttribute("data-testid") || "",
    });
    // Spotify retains ownership of SVG children, events, and accessible names.
    for (const svg of control.querySelectorAll("svg")) {
      if (svg.closest(selector) !== control) continue;
      if (name) {
        if (svg.getAttribute("data-lg-icon") !== name) svg.setAttribute("data-lg-icon", name);
      } else {
        svg.removeAttribute("data-lg-icon");
      }
    }
  }

  function scan(node) {
    if (!(node instanceof Element) || !node.isConnected) return;
    const control = node.closest(selector);
    if (control) decorate(control);
    for (const descendant of node.querySelectorAll(selector)) decorate(descendant);
  }

  function schedule(node) {
    if (!(node instanceof Element)) return;
    pending.add(node);
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (disposed) return;
      const nodes = [...pending];
      pending.clear();
      for (const element of nodes) scan(element);
    });
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === "attributes") schedule(record.target);
      else {
        for (const node of record.addedNodes) schedule(node);
      }
    }
  });
  observer.observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["aria-label", "title", "data-testid"],
  });
  scan(document.body);
  return () => {
    disposed = true;
    observer.disconnect();
    cancelAnimationFrame(frame);
    pending.clear();
    for (const svg of document.querySelectorAll("svg[data-lg-icon]")) svg.removeAttribute("data-lg-icon");
  };
}
