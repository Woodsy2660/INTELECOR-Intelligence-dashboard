import structlog
from jinja2 import Template
from api.config import get_settings

logger = structlog.get_logger()

EMAIL_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a2e;">
  <div style="background: #2F5496; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 20px;">INTELECOR Practice Briefing</h1>
    <p style="color: #b8d4f0; margin: 4px 0 0; font-size: 13px;">{{ period }}</p>
  </div>

  <div style="padding: 20px; background: #f8f9fa; border: 1px solid #e0e0e0;">
    {% if summary %}
    <div style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #2F5496;">
      <p style="margin: 0; font-size: 14px; line-height: 1.6;">{{ summary }}</p>
    </div>
    {% endif %}

    <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px;">
      <tr style="background: #2F5496; color: white;">
        <td style="padding: 10px 14px; font-size: 13px; font-weight: bold;">Metric</td>
        <td style="padding: 10px 14px; font-size: 13px; font-weight: bold; text-align: right;">This Week</td>
      </tr>
      <tr><td style="padding: 8px 14px; border-bottom: 1px solid #eee;">Revenue collected</td>
          <td style="padding: 8px 14px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">${{ financial.total_received }}</td></tr>
      <tr><td style="padding: 8px 14px; border-bottom: 1px solid #eee;">Outstanding</td>
          <td style="padding: 8px 14px; border-bottom: 1px solid #eee; text-align: right; color: {% if financial.total_outstanding > 2000 %}#EB5757{% else %}#27AE60{% endif %};">${{ financial.total_outstanding }}</td></tr>
      <tr><td style="padding: 8px 14px; border-bottom: 1px solid #eee;">Collection rate</td>
          <td style="padding: 8px 14px; border-bottom: 1px solid #eee; text-align: right;">{{ financial.collection_rate }}%</td></tr>
      <tr><td style="padding: 8px 14px; border-bottom: 1px solid #eee;">Patients seen</td>
          <td style="padding: 8px 14px; border-bottom: 1px solid #eee; text-align: right;">{{ operations.summary.total_completed }}</td></tr>
      <tr><td style="padding: 8px 14px; border-bottom: 1px solid #eee;">DNA rate</td>
          <td style="padding: 8px 14px; border-bottom: 1px solid #eee; text-align: right;">{{ operations.summary.dna_rate }}%</td></tr>
      <tr><td style="padding: 8px 14px;">Unsigned letters</td>
          <td style="padding: 8px 14px; text-align: right; color: {% if documents.total_unsigned > 15 %}#EB5757{% elif documents.total_unsigned > 5 %}#F2994A{% else %}#27AE60{% endif %}; font-weight: bold;">{{ documents.total_unsigned }}</td></tr>
    </table>

    {% if financial.leakage_flags %}
    <div style="margin-top: 16px; background: white; padding: 14px; border-radius: 8px; border-left: 4px solid #EB5757;">
      <p style="margin: 0 0 8px; font-weight: bold; font-size: 13px; color: #EB5757;">Action Required</p>
      {% for flag in financial.leakage_flags[:3] %}
      <p style="margin: 4px 0; font-size: 13px;">• {{ flag.detail }} ({{ flag.reference_id }})</p>
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <div style="padding: 12px 20px; background: #e8e8e8; border-radius: 0 0 8px 8px; text-align: center;">
    <p style="margin: 0; font-size: 11px; color: #888;">INTELECOR Practice Intelligence — intelecor.com.au</p>
  </div>
</body>
</html>
"""


class EmailDigestService:
    """Builds and sends the morning practice briefing email."""

    def send(self, tenant_id: str, results: dict | None = None, summary: str = ""):
        settings = get_settings()

        if not results:
            logger.warning("email_digest.no_results", tenant_id=tenant_id)
            return

        template = Template(EMAIL_TEMPLATE)
        html = template.render(
            period="Weekly Practice Briefing",
            summary=summary,
            financial=results.get("financial", {}),
            operations=results.get("operations", {}),
            documents=results.get("documents", {}),
        )

        try:
            import resend
            resend.api_key = settings.resend_api_key

            resend.Emails.send({
                "from": settings.email_from,
                "to": self._get_recipients(tenant_id),
                "subject": "INTELECOR — Weekly Practice Briefing",
                "html": html,
            })
            logger.info("email_digest.sent", tenant_id=tenant_id)
        except Exception as e:
            logger.error("email_digest.failed", tenant_id=tenant_id, error=str(e))

    def _get_recipients(self, tenant_id: str) -> list[str]:
        # TODO: Pull from tenant config / user table
        return ["andrew@roycardiology.com.au"]
