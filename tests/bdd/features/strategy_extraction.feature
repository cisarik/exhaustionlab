Feature: Strategy Extraction
  As a strategy researcher
  I want to extract complete trading strategy profiles
  So that I can build a knowledge base for LLM training

  Background:
    Given a working GitHub API connection
    And a SQLite database is initialized

  Scenario: Extract strategy from GitHub repository
    Given a GitHub repository "user/trading-strategy"
    When I extract the full strategy profile
    Then the strategy should have a name
    And the strategy should have author information
    And the strategy should have a description
    And the extraction status should be "complete"

  Scenario: Extract Pine Script code from repository
    Given a repository with Pine Script files
    When I extract code from the repository
    Then I should get Pine Script source code
    And the code should contain "//@version"
    And the strategy should be marked as having code

  Scenario: Extract README documentation
    Given a repository with a README file
    When I extract documentation
    Then I should get README content
    And the strategy should be marked as having documentation

  Scenario: Parse indicators from Pine Script
    Given Pine Script code containing "ta.rsi" and "ta.macd"
    When I parse the code for indicators
    Then the indicators list should contain "RSI"
    And the indicators list should contain "MACD"

  Scenario: Parse parameters from Pine Script
    Given Pine Script code with input declarations
    When I parse the code for parameters
    Then the parameters dictionary should not be empty
    And each parameter should have a name

  Scenario: Extract features from strategy
    Given strategy code mentioning "stop loss" and "take profit"
    When I analyze features
    Then the feature "stop_loss" should be true
    And the feature "take_profit" should be true

  Scenario: Save strategy to database
    Given a complete strategy profile
    When I save the strategy to the database
    Then the strategy should be stored with a unique ID
    And I should be able to retrieve it by ID
    And the quality score should be calculated

  Scenario: Search strategies by quality
    Given 10 strategies in the database with varying quality scores
    When I search for strategies with minimum quality score of 70
    Then I should get only strategies with score >= 70
    And results should be ordered by quality score descending

  Scenario: Search strategies by platform
    Given strategies from GitHub and TradingView
    When I search for strategies from "github"
    Then all results should have platform "github"

  Scenario: Get strategies with code
    Given strategies with and without code
    When I search for strategies with code
    Then all results should have has_code = true
    And all results should have non-empty code field

  Scenario: Extract top quality strategies
    Given 100 strategies with quality scores
    When I request top 10 strategies
    Then I should get exactly 10 strategies
    And they should be ordered by quality score
    And the first strategy should have the highest score

  Scenario: Database statistics
    Given 50 strategies in database
    When I request statistics
    Then total count should be 50
    And average quality score should be calculated
    And platform breakdown should be provided
    And category breakdown should be provided

  Scenario: Batch extraction from multiple repositories
    Given a list of 5 GitHub repositories
    When I extract all strategies in batch
    Then 5 strategies should be saved to database
    And extraction should complete without errors
    And each strategy should have quality score calculated

  Scenario: Handle extraction errors gracefully
    Given a repository that doesn't exist
    When I attempt to extract the strategy
    Then extraction status should be "failed"
    And extraction notes should contain error message
    And no exception should be raised

  Scenario: Calculate quality score components
    Given a strategy with known metrics
    When quality score is calculated
    Then source score should be between 0 and 100
    And code score should be between 0 and 100
    And community score should be between 0 and 100
    And final score should be weighted average

  # Integration Pipeline Scenarios
  Scenario: End-to-end extraction pipeline
    Given a GitHub search query "crypto momentum strategy"
    When I run the complete extraction pipeline
    Then strategies should be discovered
    And code should be extracted from repositories
    And quality scores should be calculated
    And strategies should be saved to database
    And pipeline statistics should be available

  Scenario: Pipeline with filtering and ranking
    Given a search query returning 10 repositories
    And a minimum quality threshold of 60
    When I run the filtered pipeline
    Then only strategies with quality >= 60 should be saved
    And saved strategies should be ranked by quality
    And pipeline should report filtered count

  Scenario: Concurrent extraction with thread pool
    Given 5 GitHub repositories to extract
    When I run concurrent extraction with 3 workers
    Then all 5 strategies should be extracted
    And extraction should use parallel processing
    And total time should be less than sequential extraction
    And no database race conditions should occur

  Scenario: Pipeline error handling and recovery
    Given a mix of valid and invalid repositories
    When I run the extraction pipeline
    Then valid repositories should be extracted successfully
    And invalid repositories should be skipped with errors logged
    And pipeline should complete without crashing
    And error statistics should be tracked

  Scenario: Incremental extraction with caching
    Given previously extracted strategies in database
    When I run extraction on same repositories
    Then already-extracted strategies should be skipped
    And only new or updated strategies should be processed
    And extraction should be faster than initial run
    And cache hit statistics should be reported
