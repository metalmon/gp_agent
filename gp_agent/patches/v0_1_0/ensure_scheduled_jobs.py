# gp_agent/patches/v0_1_0/ensure_scheduled_jobs.py
import frappe

def execute():
	"""
	Ensures that the required Scheduled Job Types for gp_agent exist.
	Creates them only if they don't already exist to prevent errors
	during `bench migrate`.
	"""
	jobs = [
		{
			"method": "gp_agent.gameplan_ai_assistant.scheduler_jobs.scheduled_agent_runs",
			"frequencies": ["Hourly", "Daily", "Daily Long", "Weekly Long"] # Frequencies as they appear in DocType
		},
		{
			"method": "gp_agent.gameplan_ai_assistant.scheduler_jobs.scheduled_process_pending_logs",
			"frequencies": ["All"] # Frequencies as they appear in DocType
		}
	]

	for job_info in jobs:
		method_path = job_info["method"]
		for freq in job_info["frequencies"]:
			filters = {"method": method_path, "frequency": freq}
			if not frappe.db.exists("Scheduled Job Type", filters):
				try:
					doc = frappe.get_doc({
						"doctype": "Scheduled Job Type",
						"method": method_path,
						"frequency": freq,
					})
					doc.insert(ignore_permissions=True)
					# Frappe handles commits during patches automatically
					print(f"Created Scheduled Job Type: {freq} - {method_path}")
				except Exception as e:
					# Log error to help with debugging if creation fails unexpectedly
					frappe.log_error(f"Patch: Failed to create Scheduled Job Type: {freq} - {method_path}", str(e))
					print(f"Error: Failed to create Scheduled Job Type: {freq} - {method_path}. See error log for details.")
			else:
				print(f"Scheduled Job Type already exists: {freq} - {method_path}") 