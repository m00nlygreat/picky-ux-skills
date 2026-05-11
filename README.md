# UX Skill - Agent & Skill Guide

이 워크스페이스는 PM/UX 기획 워크플로우를 지원하는 스킬 모음이다.

---

## 스킬 목록

### `$startup-advisor`
서비스 아이디어나 PRD를 받아 **서비스 설계 검토 -> 기술 구현 가능성 -> 린 캔버스** 순으로 분석한다.
WebSearch로 경쟁사와 시장 데이터를 실제로 조사하고, 강점, 약점, 개선 제안, 종합 판정을 제공한다.

### `$ia`
서비스 기획서나 아이디어로부터 **Information Architecture(화면 위계)**를 생성한다.
엔티티 식별 -> CRUD 매핑 -> URL 계층 설계 -> 화면 메타 테이블 순으로 작업하고 `SCREENS.md`로 저장한다.

### `$stn`
**Screen Tree Notation(STN) 표준 문법**을 정의한다.
STN 파일을 읽고, 작성하고, 검증하고, 변환할 때 공통 기준으로 사용한다. 루트 규칙, YAML imports, `<GLOBAL />`, 컴포넌트 참조, optional 표기, responsive annotation, validation rule을 담당한다.

### `$design`
`SCREENS.md`의 화면 항목이나 사용자 요구사항을 받아 **STN 화면 설계**를 작성한다.
화면 목적, 정보 구조, 액션 배치, 반응형 구조, 재사용 컴포넌트 분리 여부를 판단하고, 문법은 `$stn`을 기준으로 맞춘다.
`./design/GLOBAL.md`를 공유 레이아웃으로 사용하고, 재사용 컴포넌트는 `./design/components/`에 분리 저장한다.
저장 후 `$wireframe` 실행을 제안한다.

### `$wireframe`
`./design/` 아래의 STN 파일을 읽어 **HTML 와이어프레임 뷰어**(`wireframe.html`)를 생성한다.
STN 문법 해석은 `$stn`을 기준으로 하고, LLM이 직접 STN 노드를 의미적으로 판단해 `.wf-*` 클래스 HTML로 변환한다.
기존 `wireframe.html`이 있으면 변경된 STN과 viewer template 기준으로 갱신한다.

### `$survey-advisor`
설문 질문 또는 설문 초안을 받아 **6가지 기준(예시 포함, 경험 기반, 의사결정 연결, 가설 정합, 대상 포용, 중립성)**으로 평가하고 개선안을 제안한다.

---

## 권장 워크플로우

```text
$startup-advisor   ->   $ia   ->   $design   ->   $wireframe
  아이디어 검토          화면 위계       STN 화면 설계      와이어프레임 확인
                                      ^
                                      |
                                    $stn
                               STN 공통 표준
```

각 단계의 출력은 다음 단계의 입력이 된다.
`SCREENS.md`는 `$design`의 입력이 되고, STN 파일은 `$wireframe`의 입력이 된다.
STN 문법 판단이 필요하면 `$stn`을 공통 기준으로 사용한다.

---

## $wireframe 사용 시 주의사항

### 와이어프레임은 인간 검토 전용이다

`$wireframe`의 출력(`wireframe.html`)은 **사람이 화면 구조를 눈으로 확인하기 위한 도구**다.
이 HTML을 agent에게 다시 제공하면 **시각적 레이아웃이 설계에 강하게 영향**을 미칠 수 있다.

- 와이어프레임에 나타난 배치, 크기, 시각적 비율에 끌려 STN이 변형될 수 있다.
- "와이어프레임처럼 보이게" 하려는 방향으로 설계가 왜곡될 위험이 있다.

### 이 워크플로우에서 "디자인"이란 STN 수정이다

화면 설계의 실체는 **STN 파일(`./design/*.md`, `./design/components/*.md`)**이다.
Agent가 화면 구조를 변경하거나 개선할 때는 항상 STN 파일을 직접 수정해야 한다.
와이어프레임 HTML은 STN의 렌더링 결과물일 뿐이며, 설계 변경의 대상이 아니다.

### 올바른 흐름

```text
[사람이 wireframe.html 확인]
        ↓
  피드백 -> STN 파일 수정 ($design 또는 직접 편집)
        ↓
  $wireframe 재실행 -> 갱신된 wireframe.html 확인
```

Agent에게 와이어프레임 피드백을 전달할 때는 HTML이 아니라 **텍스트로 된 설계 의도**를 전달한다.
