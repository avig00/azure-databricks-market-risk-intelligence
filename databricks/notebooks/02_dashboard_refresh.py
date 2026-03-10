# Databricks notebook source

from market_risk_platform.dashboard.app import build_dashboard_payload, summarize_dashboard

payload = build_dashboard_payload()
summary = summarize_dashboard(payload)
print(summary)

