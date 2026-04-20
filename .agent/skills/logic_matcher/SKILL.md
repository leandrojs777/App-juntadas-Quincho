---
name: Juntada Logic Matcher
description: Logic abstraction for calculating the winning hangout options based on star/point votes from friends.
version: 1.0.0
author: Antigravity Defaults
tags:
  - matching
  - voting_system
  - data_processing
---

# Juntada Logic Matcher

This skill acts as the computational brain to decide the best Date, Location, and Activity based on the group's votes.

## Rules
1. Every friend (user) can vote on multiple proposed dates, locations, or activities. 
2. The score is given in stars (e.g., 1 to 5).
3. The option with the total highest accumulated score across all users wins in its category.
4. If there's a tie, the system will just return the tied options, or the first one randomly.
5. All logic is strictly executed via the pure python file `utils/scoring.py`.

## Implementation Details
The `utils.scoring` module provides the functions to read/write from a CSV data persistence layer. It separates UI (Streamlit) from the persistence and logic.
