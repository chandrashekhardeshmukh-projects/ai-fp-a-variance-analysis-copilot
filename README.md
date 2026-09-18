# AI FP&A Variance Analysis Copilot

An AI-enabled FP&A analytics application designed to automate P&L variance analysis, revenue driver decomposition and management commentary.

## Overview

The AI FP&A Variance Analysis Copilot helps finance teams analyze financial performance by comparing actual results against budget, forecast and prior-year performance.

The application combines deterministic financial calculations with an optional AI commentary layer to convert calculated financial insights into concise management-ready explanations.

> **Note:** This project uses illustrative/demo data and is intended for portfolio and educational purposes.

## Key Features

### 📊 P&L Variance Analysis

- Actual vs Budget analysis
- Actual vs Forecast analysis
- Actual vs Prior Year analysis
- Absolute variance
- Variance percentage
- Favorable / Unfavorable classification
- EBITDA and margin analysis

### 🎯 Revenue Price / Volume / Mix Analysis

The application decomposes revenue movements into:

- Price impact
- Volume impact
- Mix impact

The analysis includes reconciliation checks to ensure the driver impacts explain the overall revenue movement.

### 🏢 Department Analysis

Analyze financial performance across business departments and identify:

- Revenue performance
- EBITDA performance
- EBITDA margin
- Major favorable variances
- Major unfavorable variances

### 🚨 Materiality Analysis

Users can define:

- Absolute variance threshold
- Percentage variance threshold

The application automatically identifies material financial variances requiring management attention.

### 🌉 EBITDA Variance Bridge

A waterfall-style bridge explains the movement from budget EBITDA to actual EBITDA through major revenue and cost drivers.

### 🤖 AI Management Commentary

The optional AI layer converts calculated financial outputs into management-ready commentary.

The AI is provided with structured financial results rather than raw unrestricted financial data.

The design separates:

- Financial calculations
- Financial interpretation
- AI-generated commentary

If an AI API is unavailable, the application continues operating using deterministic FP&A commentary.

### 💬 Ask the P&L

Users can ask questions such as:

- Why is EBITDA below budget?
- Which department has the largest unfavorable variance?
- What are the major revenue drivers?
- Which costs are above budget?
- Summarize the current financial performance.

## Technology Stack
