import frappe

def cleanup_scheduler_jobs():
	"""Remove all scheduler jobs created by this app"""
	jobs = [
		"gp_agent.gameplan_ai_assistant.scheduler_jobs.scheduled_agent_runs",
		"gp_agent.gameplan_ai_assistant.scheduler_jobs.scheduled_process_pending_logs"
	]

	for job in jobs:
		frappe.db.delete("Scheduled Job Type", {
			"method": job
		})
	frappe.db.commit() 