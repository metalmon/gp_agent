# Copyright (c) 2025, metalmon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import os


class GPAgentSettings(Document):
	pass

	@frappe.whitelist()
	def fetch_models(self):
		"""Fetch available models from API and update options in all related doctypes"""
		try:
			# Make API request
			response = requests.get(
				f"{self.base_url}/models",
				headers={
					"Authorization": f"Bearer {self.get_password('api_key')}",
					"HTTP-Referer": frappe.utils.get_url()
				}
			)
			response.raise_for_status()
			
			# Get model list and sort alphabetically
			data = response.json()
			models = sorted([model["id"] for model in data["data"]])
			models_str = "\n".join(models)
			
			# Update options in all related doctypes
			doctypes_to_update = [
				"GP Agent Settings",
				"GP Team Settings Override",
				"GP Project Settings Override",
				"GP Discussion Settings Override"
				# Add other override doctypes here when created
			]
			
			for dt in doctypes_to_update:
				doctype = frappe.get_doc("DocType", dt)
				for field in doctype.fields:
					if field.fieldname == "model":
						field.options = models_str
				doctype.save()
			
			return models
			
		except Exception as e:
			frappe.throw(f"Failed to fetch models: {str(e)}")

	def validate(self):
		"""Validate and format fields before saving"""
		self.validate_search_settings()
		
		# Ensure context_builder is set
		if not self.context_builder:
			self.context_builder = "default"

	def validate_search_settings(self):
		"""Validate search API settings"""
		# If either credential is set, both must be set
		if self.google_search_api_key or self.google_search_engine_id:
			if not (self.google_search_api_key and self.google_search_engine_id):
					frappe.throw(
						"Both Google Search API Key and Search Engine ID must be configured"
					)

	@frappe.whitelist()
	def update_system_prompt(self, language="ru"):
		"""Update system and tools prompts from default files"""
		try:
			# Get the module path
			module_path = frappe.get_module_path("gameplan_ai_assistant")
			
			# Select files based on language
			system_file = "default_system_prompt.md" if language == "ru" else "default_system_prompt_en.md"
			tools_file = "default_tools_prompt.md" if language == "ru" else "default_tools_prompt_en.md"
			
			system_prompt_file = os.path.join(module_path, "doctype", "gp_agent_settings", system_file)
			tools_prompt_file = os.path.join(module_path, "doctype", "gp_agent_settings", tools_file)
			
			# Read the default prompts
			with open(system_prompt_file, 'r', encoding='utf-8') as f:
				default_system_prompt = f.read()
				
			with open(tools_prompt_file, 'r', encoding='utf-8') as f:
				default_tools_prompt = f.read()
			
			# Update the document
			self.system_prompt = default_system_prompt
			self.tools_prompt = default_tools_prompt
			
			# Ensure context_builder is set
			if not self.context_builder:
				self.context_builder = "default"
				
			self.save()
			
			frappe.msgprint("System and tools prompts updated successfully")
			
		except Exception as e:
			frappe.throw(f"Failed to update prompts: {str(e)}")
