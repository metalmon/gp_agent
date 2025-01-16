# Copyright (c) 2025, metalmon and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from typing import Dict, Any, Optional


@frappe.whitelist()
def process_pending():
	"""Process pending GP Agent Logs"""
	settings = frappe.get_single("GP Agent Settings")
	
	# Skip if processing is disabled
	if not settings.enabled:
		frappe.msgprint("GP Agent processing is disabled")
		return
		
	try:
		from gp_agent.gameplan_ai_assistant.scheduler_jobs import process_pending_logs
		process_pending_logs(is_background=False)
	except Exception as e:
		frappe.log_error(
			title="GP Agent Processing Error",
			message=f"Error in process_pending: {str(e)}"
		)
		frappe.throw(f"Error processing pending logs: {str(e)}")
		


class GPAgentLog(Document):
	def validate(self):
		"""Validate document before saving"""
		self.sync_all_content_fields()
	
	def onload(self):
		"""Extract content from JSON fields when form is loaded"""
		self.sync_all_content_fields()
	
	def sync_all_content_fields(self):
		"""Sync all JSON fields with their content representations"""
		self._sync_field('context')
		self._sync_field('system_prompt')
		self._sync_field('messages')
		self._sync_field('tools')
		self._sync_field('tool_context')
		self._sync_field('response')
	
	def _sync_field(self, field_name: str):
		"""Sync a single JSON field with its content representation"""
		json_field = getattr(self, field_name, None)
		if json_field:
			try:
				data = json.loads(json_field) if isinstance(json_field, str) else json_field
				setattr(
					self,
					f"{field_name}_content",
					json.dumps(data, ensure_ascii=False, indent=2)
				)
			except (json.JSONDecodeError, TypeError) as e:
				frappe.log_error(f"Error syncing {field_name}: {str(e)}")
				setattr(self, f"{field_name}_content", str(json_field))
	
	def set_model_params(self, settings: Dict[str, Any]):
		"""Set model parameters from settings"""
		self.temperature = settings.get('temperature')
		self.max_tokens = settings.get('max_tokens')
		self.top_p = settings.get('top_p')
		self.top_k = settings.get('top_k')
		self.context_depth = settings.get('context_depth')
	
	def get_model_params(self) -> Dict[str, Any]:
		"""Get model parameters as dictionary"""
		return {
			"temperature": self.temperature,
			"max_tokens": self.max_tokens,
			"top_p": self.top_p,
			"top_k": self.top_k
		}
	
	def update_token_usage(self, usage_data: Dict[str, int]):
		"""Update token usage statistics"""
		self.prompt_tokens = usage_data.get('prompt_tokens', 0)
		self.completion_tokens = usage_data.get('completion_tokens', 0)
		self.total_tokens = usage_data.get('total_tokens', 0)
	
	def set_response(self, response_data: Dict[str, Any]):
		"""Set response data and update token usage"""
		self.response = json.dumps(response_data)
		
		# Update token usage if available
		if "usage" in response_data:
			self.update_token_usage(response_data["usage"])
		
		# Sync response content
		self._sync_field('response')
	
	def get_response(self) -> Optional[Dict[str, Any]]:
		"""Get response data as dictionary"""
		try:
			return json.loads(self.response) if self.response else None
		except (json.JSONDecodeError, TypeError):
			return None
	
	def get_settings(self) -> Dict[str, Any]:
		"""Get settings for tools
		
		Returns:
			Dictionary containing all settings needed by tools
		"""
		settings = frappe.get_single("GP Agent Settings")
		return {
			# API settings
			"api_schema": settings.api_schema,
			"base_url": settings.base_url,
			"api_key": settings.get_password("api_key"),
			
			# Model settings
			"model": self.model,
			"temperature": self.temperature,
			"max_tokens": self.max_tokens,
			"top_p": self.top_p,
			"top_k": self.top_k,
			
			# Context settings
			"context_depth": self.context_depth,
			"chat_memory": settings.chat_memory,
			
			# Search settings
			"google_api_key": settings.get_password("google_search_api_key"),
			"google_search_engine_id": settings.google_search_engine_id
		}
		
