frappe.listview_settings['GP Agent Log'] = {
	add_fields: ['status', 'is_tool_call'],
	get_indicator: function(doc) {
		let status_colors = {
			'Queued': 'blue',
			'Processing': 'orange',
			'Completed': 'green',
			'Error': 'yellow',
			'Failed': 'red'
		};

		let indicator_text = __(doc.status);
		if (doc.is_tool_call) {
			indicator_text += ' • Tool Call';
		}

		return [
			indicator_text,
			status_colors[doc.status],
			'status,=,' + doc.status
		];
	},
	onload: function(listview) {
		listview.page.add_inner_button(__('Process Pending'), function() {
			frappe.call({
				method: 'gp_agent.gameplan_ai_assistant.doctype.gp_agent_log.gp_agent_log.process_pending',
				callback: function(r) {
					frappe.show_alert({
						message: __('Processing pending logs...'),
						indicator: 'blue'
					});
					listview.refresh();
				}
			});
		});
	}
}; 