import html
import smtplib
from email.message import EmailMessage
from typing import Any

from app.config import (
    ALERT_EMAIL_ENABLED,
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
    EMAIL_APP_PASSWORD,
    EMAIL_USERNAME,
    SMTP_HOST,
    SMTP_PORT,
)
from app.models.incident import Incident


def _is_configured() -> bool:
    return bool(
        ALERT_EMAIL_ENABLED
        and ALERT_EMAIL_FROM
        and ALERT_EMAIL_TO
        and EMAIL_USERNAME
        and EMAIL_APP_PASSWORD
        and SMTP_HOST
        and SMTP_PORT
    )


def get_alert_status() -> dict:
    return {
        "enabled": ALERT_EMAIL_ENABLED,
        "configured": _is_configured(),
        "from_email": ALERT_EMAIL_FROM,
        "to_email": ALERT_EMAIL_TO,
        "smtp_host": SMTP_HOST,
        "smtp_port": SMTP_PORT,
    }


def _list_items(values: list[Any]) -> str:
    if not values:
        return "<li>None detected yet.</li>"

    return "".join(f"<li>{html.escape(str(value))}</li>" for value in values)


def _cluster_items(clusters: list[dict]) -> str:
    if not clusters:
        return "<li>No root cause clusters detected yet.</li>"

    items = []
    for cluster in clusters:
        theme = html.escape(str(cluster.get("theme", "Operational issue cluster")))
        count = html.escape(str(cluster.get("workflow_count", "")))
        summary = html.escape(str(cluster.get("summary", "")))
        count_text = f" ({count} workflows)" if count else ""
        summary_text = f"<div style=\"color:#9ca3af;margin-top:4px;\">{summary}</div>" if summary else ""
        items.append(f"<li><strong>{theme}</strong>{count_text}{summary_text}</li>")

    return "".join(items)


def _plain_text(
    incident: Incident,
    intelligence: dict,
    related_workflow_ids: list[int],
    reason: str,
) -> str:
    clusters = intelligence.get("root_cause_clusters", [])
    cluster_lines = [
        f"- {cluster.get('theme', 'Operational issue cluster')}: {cluster.get('summary', '')}"
        for cluster in clusters
    ] or ["- No root cause clusters detected yet."]

    risks = [f"- {risk}" for risk in intelligence.get("operational_risks", [])] or ["- None detected yet."]
    actions = [f"- {action}" for action in intelligence.get("recommended_actions", [])] or ["- Review affected workflows."]

    return "\n".join(
        [
            f"OpsPilot incident alert ({reason})",
            f"Category: {incident.category}",
            f"Severity: {incident.severity}",
            f"Workflow count: {incident.workflow_count}",
            f"Related workflows: {', '.join(str(workflow_id) for workflow_id in related_workflow_ids) or 'None'}",
            "",
            "Root cause clusters:",
            *cluster_lines,
            "",
            "Operational risks:",
            *risks,
            "",
            "Recommended actions:",
            *actions,
        ]
    )


def _html_body(
    incident: Incident,
    intelligence: dict,
    related_workflow_ids: list[int],
    reason: str,
) -> str:
    category = html.escape(incident.category)
    severity = html.escape(incident.severity.upper())
    title = html.escape(incident.title)
    workflow_count = html.escape(str(incident.workflow_count))
    related_ids = ", ".join(str(workflow_id) for workflow_id in related_workflow_ids) or "None"
    related_ids = html.escape(related_ids)
    reason_label = "New incident detected" if reason == "created" else "Incident severity escalated"

    clusters = _cluster_items(intelligence.get("root_cause_clusters", []))
    risks = _list_items(intelligence.get("operational_risks", []))
    actions = _list_items(intelligence.get("recommended_actions", []))

    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#0b1020;color:#e5e7eb;font-family:Inter,Arial,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0b1020;padding:28px;">
      <tr>
        <td align="center">
          <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;background:#111827;border:1px solid #253044;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px;border-bottom:1px solid #253044;">
                <div style="color:#38bdf8;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;">OpsPilot Incident Alert</div>
                <h1 style="margin:10px 0 0;font-size:26px;line-height:1.25;color:#f9fafb;">{title}</h1>
                <p style="margin:10px 0 0;color:#9ca3af;">{html.escape(reason_label)}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding:14px;border:1px solid #253044;border-radius:12px;background:#0f172a;">
                      <div style="color:#9ca3af;font-size:12px;text-transform:uppercase;">Category</div>
                      <div style="margin-top:6px;font-size:18px;font-weight:700;">{category}</div>
                    </td>
                    <td width="12"></td>
                    <td style="padding:14px;border:1px solid #253044;border-radius:12px;background:#0f172a;">
                      <div style="color:#9ca3af;font-size:12px;text-transform:uppercase;">Severity</div>
                      <div style="margin-top:6px;font-size:18px;font-weight:800;color:#f59e0b;">{severity}</div>
                    </td>
                    <td width="12"></td>
                    <td style="padding:14px;border:1px solid #253044;border-radius:12px;background:#0f172a;">
                      <div style="color:#9ca3af;font-size:12px;text-transform:uppercase;">Workflows</div>
                      <div style="margin-top:6px;font-size:18px;font-weight:700;">{workflow_count}</div>
                    </td>
                  </tr>
                </table>

                <h2 style="margin:28px 0 10px;font-size:18px;">Root cause clusters</h2>
                <ul style="margin:0;padding-left:20px;color:#d1d5db;line-height:1.6;">{clusters}</ul>

                <h2 style="margin:28px 0 10px;font-size:18px;">Operational risks</h2>
                <ul style="margin:0;padding-left:20px;color:#d1d5db;line-height:1.6;">{risks}</ul>

                <h2 style="margin:28px 0 10px;font-size:18px;">Recommended actions</h2>
                <ul style="margin:0;padding-left:20px;color:#d1d5db;line-height:1.6;">{actions}</ul>

                <div style="margin-top:28px;padding:16px;border-radius:12px;background:#0f172a;border:1px solid #253044;">
                  <div style="color:#9ca3af;font-size:12px;text-transform:uppercase;">Related workflow IDs</div>
                  <div style="margin-top:6px;color:#f9fafb;">{related_ids}</div>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def send_incident_alert(
    incident: Incident,
    intelligence: dict,
    related_workflow_ids: list[int],
    reason: str,
) -> bool:
    if not _is_configured():
        return False

    print("[alert_service] sending incident alert")

    message = EmailMessage()
    message["Subject"] = f"[OpsPilot] {incident.severity.upper()} {incident.category} incident alert"
    message["From"] = ALERT_EMAIL_FROM
    message["To"] = ALERT_EMAIL_TO
    message.set_content(_plain_text(incident, intelligence, related_workflow_ids, reason))
    message.add_alternative(
        _html_body(incident, intelligence, related_workflow_ids, reason),
        subtype="html",
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_APP_PASSWORD)
            server.send_message(message)
    except Exception as exc:
        print(f"[alert_service] alert failed: {exc}")
        return False

    print("[alert_service] alert sent successfully")
    return True
