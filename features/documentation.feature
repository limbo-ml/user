Feature: Documentation

    Scenario: Module documentation
        Given all public modules
        And the reference documentation
        Then every module must have a section in the reference documentation except []
        And every section in the reference documentation must match a module

    Scenario: Documentation notebooks
        Given all documentation notebooks
        Then every notebook runs without error

