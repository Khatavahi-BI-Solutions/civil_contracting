# -*- coding: utf-8 -*-
# Copyright (c) 2015, Revant Nandgaonkar and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from collections import Counter

class RunningAccountBill(Document):

	def validate(self):
		self.validate_previous_ra_bill()
		self.validate_project()
		self.set_ra_bill_no()
		self.validate_ra_no()
		self.validate_prev_si()

	def validate_prev_si(self):
		if self.prev_ra_bill:
			for invoice in self.sales_invoice_list:
				prev_ra_bill = frappe.get_list("Running Account Bill Invoices",
					fields=["sales_invoice"],
					filters = {
						"parent": self.prev_ra_bill
					})
				for i in xrange(len(prev_ra_bill)):
					if invoice.sales_invoice == prev_ra_bill[i].sales_invoice:
						frappe.throw(_("Cannot Select Sales Invoices from Previous RA Bill"))

	def validate_ra_no(self):
		""" Validates Same RA Bill cannot be selected as Previous RA Bill"""
		if self.prev_ra_bill and self.prev_ra_bill == self.name:
			frappe.throw(_("Cannot Select Previous RA Bill on Same Document"))

	def validate_previous_ra_bill(self):
		"""Validate customer of current RA Bill and Previous RA Bill to be equal"""
		if self.prev_ra_bill and frappe.db.get_value("Running Account Bill", self.prev_ra_bill, "customer") != self.customer:
			frappe.throw(_("Previous Running Account Bill Customer does not match with current"))

	def validate_project(self):
		"""Validate Project's Customer and RA Bill's Customer to be same"""
		if self.project and frappe.db.get_value("Project", self.project, "customer") != self.customer:
			frappe.throw(_("Project's Customer does not match with current"))

	def set_ra_bill_no(self):
		"""Set RA Bill No depending on Selected Previous RA Bill or set it to 1"""
		if self.prev_ra_bill:
			prev_ra_bill_no = frappe.db.get_value("Running Account Bill", self.prev_ra_bill, "ra_bill_no")
			self.ra_bill_no = int(prev_ra_bill_no) + 1
		else:
			self.ra_bill_no = 1

	def get_ra_items(self):
		"""get_ra_items"""
		item_list = []
		out_list = []
		for i in self.get("sales_invoice_list"):
			item_list.append(frappe.db.sql("""select item_code, qty, rate, stock_uom, amount
			from `tabSales Invoice Item`
			where parent = %(parent)s"""\
			, {"parent":i.sales_invoice}, as_dict=1))

		for item in item_list:
			for i in range(0,len(item)):
				out_list.append({
					"item_code": item[i].item_code,
					"qty": item[i].qty,
					"stock_uom": item[i].stock_uom,
					"rate": item[i].rate,
					"amount": item[i].amount,
					"previous_qty": 0.0
				})

		for i,a in enumerate(out_list):
		    z=0
		    for b in out_list[i+1:]:
		        if a['item_code']==b['item_code']:
		            a['qty'] += b['qty']
		            out_list.pop(out_list.index(b))
		            z=1
		
		if self.prev_ra_bill:
			for item in out_list:
				item['previous_qty'] = frappe.db.get_value("Running Account Bill Items", {"parent":self.prev_ra_bill, "item":item['item_code']}, "total_qty")

		return out_list

@frappe.whitelist()
def get_sales_invoices(customer, project=None, prev_ra_bill=None):
	if customer and project:
		out = frappe.db.sql("""select name, total, total_taxes_and_charges, grand_total, paid_amount
			from `tabSales Invoice`
			where customer = %(customer)s and
			project_name = %(project)s and
			docstatus = 1 """\
			, {"customer":frappe.db.escape(customer),"project":frappe.db.escape(project)}, as_dict=1)
	elif customer:
		out = frappe.db.sql("""select name, total, total_taxes_and_charges, grand_total, paid_amount
			from `tabSales Invoice`
			where customer = %(customer)s and
			docstatus = 1 """\
			, {"customer":frappe.db.escape(customer)}, as_dict=1)

	ra = frappe.get_list("Running Account Bill Invoices",
			fields=["sales_invoice"],
			filters = {
				"parent": prev_ra_bill
			})
	for i in xrange(len(ra)):
		for item in out:
			if ra[i].sales_invoice == item.name:
				out.remove(item)

	return out
