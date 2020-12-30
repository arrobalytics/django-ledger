Feature: Explaining Behavioral Driven Development Tests

  Scenario Outline: The user wants to know how much is the sum of two numbers
    Given that we know what the two numbers are <n1> and <n2>
    When we add both numbers
    Then we get back the correct result <result>
    Examples:
      | n1  | n2   | result |
      | 3.4 | 2.5  | 5.9    |
      | 7.0 | -4.3 | 2.7    |



