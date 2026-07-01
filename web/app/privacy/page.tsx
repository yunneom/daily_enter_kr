import AppShell from "@/components/AppShell";

export const metadata = {
  title: "개인정보처리방침 — 이상형 월드컵",
  description: "이상형 월드컵 서비스의 개인정보처리방침.",
};

const UPDATED = "2026-07-01";
const VERSION = "1.0";

export default function PrivacyPage() {
  return (
    <AppShell title="개인정보처리방침">
      <div className="legal-doc">
        <p className="legal-meta">
          최종 개정일 {UPDATED} · 버전 {VERSION}
        </p>

        <p>
          본 방침은 이상형 월드컵 서비스(이하 &ldquo;서비스&rdquo;)가 이용자의 정보를
          어떻게 다루는지를 설명합니다. 서비스는 이름, 연락처 등 개인을 특정할 수 있는
          정보를 수집하지 않습니다.
        </p>

        <h2>1. 수집 항목</h2>
        <p>
          서비스는 중복 투표 방지 목적에 한하여 다음의 최소 정보만을 처리합니다.
        </p>
        <ul>
          <li>브라우저 기기 식별자(device_id): 브라우저에 저장되는 임의의 식별값</li>
          <li>접속 IP 주소의 해시값: 원본 IP를 저장하지 않고 해시 처리한 값</li>
        </ul>
        <p>
          위 정보는 한 사람이 같은 월드컵을 여러 번 집계에 반영하는 것을 막기 위한
          용도로만 사용되며, 이름·이메일·전화번호 등 개인정보는 수집하지 않습니다.
        </p>

        <h2>2. 쿠키 및 로컬 저장소</h2>
        <p>
          참여 진행 상태 저장과 중복 참여 방지를 위해 브라우저의 로컬 저장소와 쿠키를
          사용합니다. 브라우저 설정에서 저장 데이터를 삭제할 수 있으나, 이 경우 진행
          중이던 참여 기록이 사라질 수 있습니다.
        </p>

        <h2>3. 제3자 광고</h2>
        <p>
          서비스에는 Google AdSense 등 제3자 광고가 게재될 수 있습니다. 광고 사업자는
          쿠키를 사용하여 이용자의 관심에 기반한 광고를 제공할 수 있습니다. Google의
          광고에 사용되는 쿠키는 다음 페이지에서 설정하거나 사용을 중지(옵트아웃)할 수
          있습니다.
        </p>
        <p className="legal-link">https://www.google.com/settings/ads</p>

        <h2>4. 데이터 보관 및 목적</h2>
        <p>
          수집된 식별 정보는 집계 무결성 유지 목적으로만 보관되며, 목적 달성 후에는
          집계 통계 형태로만 남습니다. 개별 참여 기록을 제3자에게 판매하거나 제공하지
          않습니다.
        </p>

        <h2>5. 문의</h2>
        <p>
          개인정보 처리에 관한 문의는 운영 계정 @daily_enter_kr 으로 연락해 주시기
          바랍니다.
        </p>
      </div>
    </AppShell>
  );
}
