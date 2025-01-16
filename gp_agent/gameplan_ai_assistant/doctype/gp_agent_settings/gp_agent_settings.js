// Copyright (c) 2025, metalmon and contributors
// For license information, please see license.txt

frappe.ui.form.on("GP Agent Settings", {
	refresh: function(frm) {
		frm.add_custom_button(__('Run Now'), function() {
			frappe.call({
				method: "gp_agent.gameplan_ai_assistant.api.schedule_agent_runs",
				callback: function(r) {
					frappe.show_alert({
						message: __('Created test agent log'),
						indicator: 'green'
					});
				}
			});
		});

		frm.add_custom_button(__('Fetch models'), function() {
			frm.call({
				doc: frm.doc,
				method: 'fetch_models',
				callback: function(r) {
					if (r.message) {
						// Sort models alphabetically and update options
						const sortedModels = r.message.sort();
						frm.set_df_property('model', 'options', sortedModels.join('\n'));
						frm.refresh_field('model');
						frappe.show_alert({
							message: __('Models fetched successfully'),
							indicator: 'green'
						});
					}
				}
			});
		});

		frm.add_custom_button(__('Update System Prompt'), function() {
			let d = new frappe.ui.Dialog({
				title: __('Select System Prompt Language'),
				fields: [
					{
						label: __('Language'),
						fieldname: 'language',
						fieldtype: 'Select',
						options: [
							{ label: __('Russian'), value: 'ru' },
							{ label: __('English'), value: 'en' }
						],
						default: 'ru'
					}
				],
				primary_action_label: __('Update'),
				primary_action(values) {
					frm.call('update_system_prompt', {
						language: values.language
					}).then(() => {
						d.hide();
						frm.reload_doc();
					});
				}
			});
			d.show();
		}, __('Actions'));
	},

	fetch_avialable: function(frm) {
		if (!frm.doc.base_url || !frm.doc.api_key) {
			frappe.msgprint(__("Please enter Base URL and API Key first"));
			return;
		}

		frappe.call({
			method: "gp_agent.gameplan_ai_assistant.doctype.gp_agent_settings.gp_agent_settings.fetch_models",
			args: {
				base_url: frm.doc.base_url,
				api_key: frm.doc.api_key
			},
			callback: function(response) {
				if (response.exc) {
					frappe.msgprint(__("Failed to fetch models. Please check your Base URL and API Key."));
					return;
				}

				let models = response.message.data || [];
				let model_list = models.map(model => model.id);

				if (model_list.length === 0) {
					frappe.msgprint(__("No models found"));
					return;
				}

				// Если модель не выбрана, выбираем первую из списка
				if (!frm.doc.model) {
					frm.set_value("model", model_list[0]);
				}
				
				// Перезагружаем форму для обновления опций
				frm.reload_doc().then(() => {
					frappe.msgprint(__("Models list updated successfully"));
				});
			}
		});
	}
}); 