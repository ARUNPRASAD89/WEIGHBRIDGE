"""
Email Manager Core - Backend Logic (No PyQt5 imports)
Handles email scheduling, report generation, and sending
UPDATED: With "No Records Found" handling
"""

import smtplib
import ssl
import json
import logging
from datetime import datetime, timedelta, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
import threading

from db_utils import fetch_one, fetch_all, execute_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [EMAIL] - %(message)s'
)
logger = logging.getLogger(__name__)


# --- DYNAMIC FIELD LOADER ---
class TicketFieldLoader:
    """Dynamically load available fields from tickets table"""
    
    @staticmethod
    def get_available_fields() -> List[Dict]:
        """Get all fields available in tickets table"""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tickets'
            ORDER BY ordinal_position
        """
        try:
            fields = fetch_all(query)
            return fields or []
        except Exception as e:
            logger.error(f"Error fetching ticket fields: {e}")
            return []
    
    @staticmethod
    def get_field_names() -> List[str]:
        """Get list of field names only"""
        fields = TicketFieldLoader.get_available_fields()
        return [f['column_name'] for f in fields]
    
    @staticmethod
    def get_field_display_names() -> Dict[str, str]:
        """Get field names with friendly display names"""
        fields = TicketFieldLoader.get_available_fields()
        display_names = {}
        
        for field in fields:
            col_name = field['column_name']
            # Convert "TicketNumber" -> "Ticket Number"
            display_name = ''.join([' ' + c if c.isupper() else c for c in col_name]).strip()
            display_names[col_name] = display_name
        
        return display_names



# --- DYNAMIC AGGREGATOR ---
class DynamicAggregator:
    """Dynamically aggregate fields based on user configuration"""
    
    @staticmethod
    def get_aggregation_types() -> List[str]:
        """Get available aggregation types"""
        return ["COUNT", "SUM", "AVG", "MIN", "MAX"]
    
    
    
    @staticmethod
    def build_aggregation_query(
        selected_fields: List[str],
        aggregation_config: Optional[Dict] = None,
        date_range: Tuple[date, date] = None
    ) -> str:
        """Build SQL query with aggregations - WITHOUT Closed filter"""
        
        if not selected_fields:
            logger.warning("No selected fields provided")
            return None
        
        select_parts = []
        group_by_parts = []
        
        # Add selected fields to SELECT and GROUP BY
        for field in selected_fields:
            if field:
                field_safe = f'"{field}"'
                select_parts.append(field_safe)
                
                # Only group by non-aggregated fields
                if field not in ['NetWeight', 'EmptyWeight', 'LoadedWeight', 'EAMOUNT', 'LAMOUNT', 'TAMOUNT']:
                    group_by_parts.append(field_safe)
        
        # Add aggregations
        if aggregation_config:
            display_names = TicketFieldLoader.get_field_display_names()
            reverse_mapping = {v: k for k, v in display_names.items()}
            
            for display_name, agg_type in aggregation_config.items():
                if agg_type and display_name:
                    agg_func = str(agg_type).upper()
                    if agg_func in ["COUNT", "SUM", "AVG", "MIN", "MAX"]:
                        col_name = reverse_mapping.get(display_name, display_name)
                        
                        if col_name and col_name in TicketFieldLoader.get_field_names():
                            select_parts.append(f'{agg_func}("{col_name}") AS "{col_name}_{agg_func}"')
                            logger.debug(f"Added aggregation: {agg_func}({col_name})")
        
        if not select_parts:
            logger.warning("No select parts built")
            return None
        
        select_clause = ', '.join(select_parts)
        
        # Build WHERE clause - REMOVED "Closed" = TRUE
        where_clause = "1=1"  # Always true, so we can add AND conditions
        if date_range:
            start_date, end_date = date_range
            where_clause += f' AND "Date" >= \'{start_date}\' AND "Date" <= \'{end_date}\''
        
        # Build GROUP BY clause if needed
        if group_by_parts and aggregation_config:
            group_by_clause = f"GROUP BY {', '.join(group_by_parts)}"
            query = f"""
                SELECT {select_clause}
                FROM tickets
                WHERE {where_clause}
                {group_by_clause}
                ORDER BY "Date" DESC
            """
        else:
            query = f"""
                SELECT {select_clause}
                FROM tickets
                WHERE {where_clause}
                ORDER BY "Date" DESC
            """
        
        logger.info(f"Generated query:\n{query}")
        
        return query
    
    @staticmethod
    def execute_aggregation_query(
        selected_fields: List[str],
        aggregation_config: Optional[Dict] = None,
        date_range: Tuple[date, date] = None
    ) -> List[Dict]:
        """Execute aggregation query"""
        
        query = DynamicAggregator.build_aggregation_query(
            selected_fields,
            aggregation_config,
            date_range
        )
        
        if not query:
            logger.warning("No query built")
            return []
        
        try:
            results = fetch_all(query)
            logger.info(f"Aggregation query returned {len(results) if results else 0} rows")
            return results or []
        except Exception as e:
            logger.error(f"Error executing aggregation query: {e}")
            logger.debug(f"Query was: {query}")
            return []


# --- DYNAMIC REPORT GENERATOR ---
class DynamicReportGenerator:
    """Generate reports using user-selected fields"""
    
    @staticmethod
    def get_date_range(report_type: str) -> Tuple[date, date]:
        """Calculate date range for report type"""
        today = date.today()
        
        if report_type == "DAILY":
            start_date = today - timedelta(days=1)
            end_date = today
            
        elif report_type == "WEEKLY":
            start_date = today - timedelta(days=7)
            end_date = today
            
        elif report_type == "MONTHLY":
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:
            start_date = today - timedelta(days=1)
            end_date = today
            
        return start_date, end_date
    
    @staticmethod
    def generate_report(
        report_type: str, 
        selected_fields: List[str],
        aggregation_config: Optional[Dict] = None,
        report_filters: Optional[Dict] = None
    ) -> Dict:
        """Generate report with user-selected fields"""
        
        start_date, end_date = DynamicReportGenerator.get_date_range(report_type)
        
        logger.info(f"Generating {report_type} report with fields: {selected_fields}")
        
        # Validate fields
        available_fields = set(TicketFieldLoader.get_field_names())
        selected_fields = [f for f in selected_fields if f in available_fields]
        
        if not selected_fields:
            logger.warning("Selected fields not found in tickets table")
            return {"error": "Selected fields invalid"}
        
        # Execute aggregation query
        tickets = DynamicAggregator.execute_aggregation_query(
            selected_fields,
            aggregation_config,
            (start_date, end_date)
        )
        
        #  NEW: Check if no records found
        if not tickets:
            logger.warning(f"No closed tickets found for {report_type} report (Date range: {start_date} to {end_date})")
            return {
                "error": "NO_RECORDS",  #  Add error flag
                "report_type": report_type,
                "date_range": f"{start_date} to {end_date}",
                "message": f"No records found for {report_type} report (Date range: {start_date} to {end_date})",
                "selected_fields": selected_fields,
                "aggregation_config": aggregation_config,
                "tickets": [],
                "total_records": 0
            }
        
        # Calculate aggregates for numeric fields
        aggregates = DynamicReportGenerator._calculate_aggregates(tickets, selected_fields)
        
        return {
            "report_type": report_type,
            "date_range": f"{start_date} to {end_date}",
            "generated_at": datetime.now().isoformat(),
            "selected_fields": selected_fields,
            "aggregation_config": aggregation_config,
            "aggregates": aggregates,
            "tickets": tickets,
            "total_records": len(tickets)
        }
    
    @staticmethod
    def _calculate_aggregates(tickets: List[Dict], selected_fields: List[str]) -> Dict:
        """Calculate sum/count for numeric fields"""
        aggregates = {}
        
        numeric_fields = ['NetWeight', 'EmptyWeight', 'LoadedWeight', 'EAMOUNT', 'LAMOUNT', 'TAMOUNT']
        
        for field in selected_fields:
            if field in numeric_fields:
                try:
                    total = sum(float(t.get(field) or 0) for t in tickets)
                    avg = total / len(tickets) if tickets else 0
                    aggregates[field] = {
                        "total": round(total, 2),
                        "average": round(avg, 2),
                        "count": len(tickets)
                    }
                except (ValueError, TypeError):
                    pass
        
        return aggregates


# --- DYNAMIC EMAIL TEMPLATE BUILDER ---
class DynamicEmailTemplateBuilder:
    """Build HTML email from report data"""
    
    @staticmethod
    def build_html_report(report_data: Dict) -> str:
        """Build HTML email dynamically"""
        
        selected_fields = report_data.get("selected_fields", [])
        tickets = report_data.get("tickets", [])
        aggregates = report_data.get("aggregates", {})
        
        display_names = TicketFieldLoader.get_field_display_names()
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0; font-size: 14px; color: #ecf0f1; }}
                .section {{ padding: 20px; border-bottom: 1px solid #ecf0f1; }}
                .section h2 {{ color: #2c3e50; margin-top: 0; font-size: 18px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; font-weight: bold; }}
                td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
                tr:hover {{ background-color: #f9f9f9; }}
                .metric {{ display: inline-block; margin-right: 30px; padding: 15px; background-color: #ecf0f1; border-radius: 5px; min-width: 200px; }}
                .metric-value {{ font-size: 20px; font-weight: bold; color: #e74c3c; }}
                .metric-label {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
                .footer {{ padding: 15px 20px; background-color: #ecf0f1; border-radius: 0 0 8px 8px; font-size: 12px; color: #7f8c8d; text-align: center; }}
                .no-data {{ padding: 20px; text-align: center; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 WEIGHBRIDGE Report</h1>
                    <p><strong>Report Type:</strong> {report_data.get('report_type', 'N/A')}</p>
                    <p><strong>Date Range:</strong> {report_data.get('date_range', 'N/A')}</p>
                    <p><strong>Generated:</strong> {report_data.get('generated_at', datetime.now().isoformat())}</p>
                </div>
        """
        
        # Add aggregates section
        if aggregates:
            html += '<div class="section"><h2>📈 Summary</h2>'
            for field_name, stats in aggregates.items():
                display_name = display_names.get(field_name, field_name)
                html += f"""
                <div class="metric">
                    <div class="metric-value">{stats['total']:.2f}</div>
                    <div class="metric-label">{display_name} (Total)</div>
                </div>
                """
            html += '</div>'
        
        # Add data table
        if tickets:
            html += '<div class="section"><h2>📋 Detailed Records</h2>'
            html += '<table><tr>'
            
            for field in selected_fields:
                display_name = display_names.get(field, field)
                html += f'<th>{display_name}</th>'
            html += '</tr>'
            
            for ticket in tickets:
                html += '<tr>'
                for field in selected_fields:
                    value = ticket.get(field, '')
                    if isinstance(value, (int, float)):
                        if value == int(value):
                            value = int(value)
                        else:
                            value = round(value, 2)
                    html += f'<td>{value}</td>'
                html += '</tr>'
            html += '</table></div>'
        else:
            html += '<div class="section"><div class="no-data">No data available for the selected period</div></div>'
        
        html += """
                <div class="footer">
                    <p><strong>WEIGHBRIDGE System</strong> | Automated Report</p>
                    <p>This is an automatically generated report. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def build_no_records_email(report_data: Dict, config_name: str) -> str:
        """Build 'No Records Found' notification email"""
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: #e74c3c; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .info {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0; font-family: monospace; font-size: 12px; }}
                .checklist {{ background-color: #e8f4f8; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .checklist ul {{ margin: 10px 0; padding-left: 20px; }}
                .checklist li {{ margin: 8px 0; }}
                .footer {{ padding: 15px 20px; background-color: #ecf0f1; border-radius: 0 0 8px 8px; font-size: 12px; color: #7f8c8d; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ No Records Found</h1>
                </div>
                <div class="content">
                    <div class="info">
                        <h2>Report Generation Notice</h2>
                        <p>Your scheduled report was generated but <strong>no data was available</strong> for the reporting period.</p>
                    </div>
                    
                    <div class="details">
                        <strong>Report Details:</strong><br>
                        Configuration: {config_name}<br>
                        Report Type: {report_data.get('report_type', 'N/A')}<br>
                        Date Range: {report_data.get('date_range', 'N/A')}<br>
                        Generated: {report_data.get('generated_at', datetime.now().isoformat())}<br>
                        Selected Fields: {', '.join(report_data.get('selected_fields', []))}
                    </div>
                    
                    <div class="checklist">
                        <h3>⚠️ What This Means:</h3>
                        <p>No closed tickets were found in the selected date range.</p>
                        <h3>✓ Please Check:</h3>
                        <ul>
                            <li><strong>Tickets in Period:</strong> Ensure tickets have been created and closed during the reporting period</li>
                            <li><strong>Ticket Status:</strong> Verify that tickets are marked as "Closed" in the system</li>
                            <li><strong>Date Range:</strong> Check if the schedule time and date range are configured correctly</li>
                            <li><strong>Filters:</strong> If filters are applied, verify they are not too restrictive</li>
                            <li><strong>System Data:</strong> Confirm that weighbridge transactions are being recorded in the tickets table</li>
                        </ul>
                    </div>
                    
                    <div class="info">
                        <h3>Next Steps:</h3>
                        <p>This is a normal notification when no data is available. Future reports will include data as soon as closed tickets exist for the reporting period.</p>
                    </div>
                </div>
                <div class="footer">
                    <p><strong>WEIGHBRIDGE System</strong> | Automated Report Notification</p>
                    <p>Configuration: {config_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


# --- EMAIL SENDER ---
# --- EMAIL SENDER ---
class EmailSender:
    """Send emails with SMTP configuration"""
    
    @staticmethod
    def test_smtp_connection(smtp_config: Dict) -> Tuple[bool, str]:
        """ NEW: Test SMTP connection"""
        try:
            logger.info(f"Testing SMTP connection to {smtp_config['smtp_server']}:{smtp_config['smtp_port']}")
            
            if smtp_config.get("use_ssl"):
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    smtp_config["smtp_server"],
                    smtp_config.get("smtp_port", 465),
                    context=context,
                    timeout=10
                ) as server:
                    server.login(smtp_config["sender_email"], smtp_config["sender_password"])
            else:
                with smtplib.SMTP(
                    smtp_config["smtp_server"],
                    smtp_config.get("smtp_port", 587),
                    timeout=10
                ) as server:
                    if smtp_config.get("use_tls"):
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(smtp_config["sender_email"], smtp_config["sender_password"])
            
            logger.info(" SMTP connection successful")
            return True, "SMTP connection successful!"
            
        except Exception as e:
            error_msg = f"SMTP connection failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def send_email(
        smtp_config: Dict,
        to_addresses: List[str],
        subject: str,
        body_html: str,
        cc_addresses: List[str] = None,
        bcc_addresses: List[str] = None
    ) -> Tuple[bool, str]:
        """Send email"""
        
        try:
            logger.info(f"Sending email to {to_addresses}")
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_config["sender_email"]
            msg["To"] = ", ".join(to_addresses)
            if cc_addresses:
                msg["CC"] = ", ".join(cc_addresses)
            
            msg.attach(MIMEText(body_html, "html"))
            
            recipients = to_addresses + (cc_addresses or []) + (bcc_addresses or [])
            
            if smtp_config.get("use_ssl"):
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    smtp_config["smtp_server"],
                    smtp_config.get("smtp_port", 465),
                    context=context
                ) as server:
                    server.login(smtp_config["sender_email"], smtp_config["sender_password"])
                    server.sendmail(smtp_config["sender_email"], recipients, msg.as_string())
            else:
                with smtplib.SMTP(smtp_config["smtp_server"], smtp_config.get("smtp_port", 587)) as server:
                    if smtp_config.get("use_tls"):
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(smtp_config["sender_email"], smtp_config["sender_password"])
                    server.sendmail(smtp_config["sender_email"], recipients, msg.as_string())
            
            logger.info(" Email sent successfully")
            return True, "Email sent successfully"
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# --- EMAIL MANAGER ---
class EmailManager:
    """Manage email scheduling and sending"""
    
    def __init__(self):
        self.stop_event = threading.Event()
        self.manager_thread = None
    
    def get_email_config(self, config_id: int) -> Optional[Dict]:
        """Fetch email configuration"""
        query = """
            SELECT * FROM emailmanager WHERE id = %s AND is_active = TRUE
        """
        return fetch_one(query, (config_id,))
    
    def list_active_configs(self) -> List[Dict]:
        """List all active configurations"""
        query = """
            SELECT * FROM emailmanager 
            WHERE is_active = TRUE
            ORDER BY id
        """
        return fetch_all(query) or []
    
    def should_send_report(self, config: Dict) -> bool:
        """Determine if report should be sent"""
        
        # ✅ CHECK AUTOSEND FIRST
        if not config.get("autosend", False):
            logger.debug(f"AutoSend disabled for config {config['id']}")
            return False
        
        report_type = config.get("report_type")
        schedule_time = config.get("schedule_time")
        last_sent = config.get("last_sent_date")
        
        if not schedule_time or not report_type:
            return False
        
        now = datetime.now()
        config_time = datetime.combine(date.today(), schedule_time).time()
        
        if now.time() < config_time:
            return False
        
        if last_sent:
            if report_type == "DAILY" and last_sent.date() == now.date():
                return False
            elif report_type == "WEEKLY" and (now - last_sent).days < 7:
                return False
            elif report_type == "MONTHLY" and last_sent.month == now.month:
                return False
        
        return True
    
    def send_scheduled_report(self, config: Dict) -> bool:
        """Generate and send scheduled report - FIXED"""
        try:
            logger.info(f"Processing email config {config['id']}: {config['email_name']}")
            
            # Get report_type first (needed everywhere)
            report_type = config.get("report_type", "DAILY")
            
            try:
                selected_fields = json.loads(config.get("selected_fields", "[]"))
            except:
                selected_fields = []
            
            try:
                aggregation_config = json.loads(config.get("aggregation_fields", "{}"))
            except:
                aggregation_config = {}
            
            if not selected_fields:
                logger.warning(f"No fields selected for config {config['id']}")
                return False
            
            # Generate report
            report_data = DynamicReportGenerator.generate_report(
                report_type, 
                selected_fields,
                aggregation_config
            )
            
            # Check for no records error
            if report_data.get("error") == "NO_RECORDS":
                logger.warning(f"No records found for config {config['id']}")
                
                # Create subject WITHOUT emoji and with proper format
                subject_template = config.get('subject_template', 'WEIGHBRIDGE {report_type} Report')
                try:
                    subject = subject_template.format(
                        report_type=report_type,
                        date=date.today().isoformat()
                    )
                except:
                    subject = f"WEIGHBRIDGE {report_type} Report - {date.today().isoformat()}"
                
                subject = f"[NO RECORDS] {subject}"  # Add prefix instead of emoji
                
                # Build no-records HTML
                body_html = DynamicEmailTemplateBuilder.build_no_records_email(report_data, config['email_name'])
                
                # Parse recipients
                try:
                    recipients = json.loads(config.get("recipient_emails", "[]"))
                except:
                    recipients = []
                
                try:
                    cc_emails = json.loads(config.get("cc_emails", "[]"))
                except:
                    cc_emails = []
                
                try:
                    bcc_emails = json.loads(config.get("bcc_emails", "[]"))
                except:
                    bcc_emails = []
                
                if not recipients:
                    logger.warning(f"No recipients configured for config {config['id']}")
                    return False
                
                # Prepare SMTP config
                smtp_config = {
                    "smtp_server": config.get("smtp_server"),
                    "smtp_port": config.get("smtp_port", 587),
                    "sender_email": config.get("sender_email"),
                    "sender_password": config.get("sender_password"),
                    "use_tls": config.get("use_tls", True),
                    "use_ssl": config.get("use_ssl", False)
                }
                
                # Send no-records notification
                success, message = EmailSender.send_email(
                    smtp_config,
                    recipients,
                    subject,
                    body_html,
                    cc_emails,
                    bcc_emails
                )
                
                # Log the send attempt
                execute_query("""
                    INSERT INTO email_send_logs 
                    (email_manager_id, report_date, report_type, recipients, status, error_message, records_count, sent_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    config["id"],
                    date.today(),
                    report_type,
                    json.dumps(recipients),
                    "sent" if success else "failed",
                    "NO RECORDS - Notification sent" if success else message,
                    0
                ))
                
                # Update last_sent_date
                if success:
                    execute_query("""
                        UPDATE emailmanager SET last_sent_date = NOW() WHERE id = %s
                    """, (config["id"],))
                
                logger.info(f"[NO-RECORDS] Email sent: {success}")
                return success
            
            # Check for other errors
            if "error" in report_data:
                logger.warning(f"Report generation failed: {report_data.get('error')}")
                return False
            
            # Build email (normal case with records)
            subject_template = config.get("subject_template", "WEIGHBRIDGE {report_type} Report")
            try:
                subject = subject_template.format(
                    report_type=report_type,
                    date=date.today().isoformat()
                )
            except:
                subject = f"WEIGHBRIDGE {report_type} Report - {date.today().isoformat()}"
            
            body_html = DynamicEmailTemplateBuilder.build_html_report(report_data)
            
            # Parse recipients
            try:
                recipients = json.loads(config.get("recipient_emails", "[]"))
            except:
                recipients = []
            
            try:
                cc_emails = json.loads(config.get("cc_emails", "[]"))
            except:
                cc_emails = []
            
            try:
                bcc_emails = json.loads(config.get("bcc_emails", "[]"))
            except:
                bcc_emails = []
            
            if not recipients:
                logger.warning(f"No recipients configured for config {config['id']}")
                return False
            
            # Prepare SMTP config
            smtp_config = {
                "smtp_server": config.get("smtp_server"),
                "smtp_port": config.get("smtp_port", 587),
                "sender_email": config.get("sender_email"),
                "sender_password": config.get("sender_password"),
                "use_tls": config.get("use_tls", True),
                "use_ssl": config.get("use_ssl", False)
            }
            
            # Send email
            success, message = EmailSender.send_email(
                smtp_config,
                recipients,
                subject,
                body_html,
                cc_emails,
                bcc_emails
            )
            
            # Log the send attempt
            execute_query("""
                INSERT INTO email_send_logs 
                (email_manager_id, report_date, report_type, recipients, status, error_message, records_count, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                config["id"],
                date.today(),
                report_type,
                json.dumps(recipients),
                "sent" if success else "failed",
                message if not success else None,
                report_data.get("total_records", 0)
            ))
            
            # Update last_sent_date
            if success:
                execute_query("""
                    UPDATE emailmanager SET last_sent_date = NOW() WHERE id = %s
                """, (config["id"],))
            
            logger.info(f"[REPORT-SENT] Email sent: {success}, Records: {report_data.get('total_records', 0)}")
            return success
            
        except Exception as e:
            logger.error(f"Error sending scheduled report: {e}", exc_info=True)
            return False
    
    def start_scheduler(self):
        """Start background scheduler"""
        if self.manager_thread and self.manager_thread.is_alive():
            logger.warning("Scheduler already running")
            return
        
        self.stop_event.clear()
        self.manager_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.manager_thread.start()
        logger.info(" Email scheduler started")
    
    def stop_scheduler(self):
        """Stop scheduler"""
        self.stop_event.set()
        if self.manager_thread:
            self.manager_thread.join(timeout=5)
        logger.info(" Email scheduler stopped")
    
    def _scheduler_loop(self):
        """Background scheduler loop"""
        while not self.stop_event.is_set():
            try:
                configs = self.list_active_configs()
                for config in configs:
                    if self.should_send_report(config):
                        self.send_scheduled_report(config)
                
                self.stop_event.wait(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self.stop_event.wait(60)


# Global instance
_email_manager = None

def get_email_manager() -> EmailManager:
    """Get or create global email manager instance"""
    global _email_manager
    if _email_manager is None:
        _email_manager = EmailManager()
    return _email_manager
