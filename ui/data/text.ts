export const guideText = {
  beginner: [
    {
      topic: "Programs",
      subcategories: {
        "1min":
          "Explain in one or two sentences what a program is, using simple everyday language.",
        "2min":
          "Give three everyday examples of tasks that could be automated with a program, and briefly explain why.",
        "4min":
          "Pick a program people already use (like a calculator or messaging app) and explain how it saves time or effort compared to doing the task manually.",
      },
    },
    {
      topic: "Variables",
      subcategories: {
        "1min":
          "Explain what the word 'variable' means in plain English, as if teaching someone new to coding.",
        "2min":
          "Show an example of a variable in code, explain what value it holds, and how that value can change.",
        "4min":
          "Demonstrate a simple program that defines three variables (a number, a word, and a true/false value) and explain what each represents.",
      },
    },
    {
      topic: "For Loops",
      subcategories: {
        "1min":
          "Explain what a loop is in plain English, and why we might use a 'for loop' instead of repeating the same code many times.",
        "2min":
          "Show a small program that uses a 'for loop' to print numbers 1 through 5, and explain how the loop knows when to stop.",
        "4min":
          "Demonstrate a 'for loop' that goes through a list of three names and prints a greeting for each, explaining how the loop repeats the same action for every item.",
      },
    },
  ],

  intermediate: [
    {
      topic: "For Loops",
      subcategories: {
        "1min":
          "Explain the difference between a 'for loop' and a 'while loop', and give an example scenario where one would be more appropriate than the other.",
        "2min":
          "Write a program that uses a 'for loop' to print only the even numbers from 1 through 10, and explain how the loop uses conditions to decide which numbers to print.",
        "4min":
          "Demonstrate a 'for loop' that iterates over a dictionary of three key-value pairs (e.g., names and ages), printing a formatted string for each entry. Explain how the loop unpacks keys and values during iteration.",
      },
    },
    {
      topic: "Functions",
      subcategories: {
        "1min":
          "Explain what a function is in programming, using one or two simple sentences.",
        "2min":
          "Demonstrate a small function that prints a greeting, call it twice, and explain why functions are reusable.",
        "4min":
          "Show a function that takes a name as input and returns a personalized message, and explain how it works.",
      },
    },
    {
      topic: "Scope",
      subcategories: {
        "1min":
          "Explain the difference between a local variable and a global variable in one or two sentences.",
        "2min":
          "Show an example with a local variable inside a function and a global variable outside, and explain how they differ.",
        "4min":
          "Demonstrate a program where a function changes a global variable, then explain what happens step by step.",
      },
    },
  ],

  expert: [
    {
      topic: "For Loops",
      subcategories: {
        "1min":
          "Discuss the trade-offs between using explicit loops (like 'for') and higher-order functions (such as 'map', 'filter', or list comprehensions) in Python. In what situations might explicit loops still be preferable?",
        "2min":
          "Write a program that uses a nested 'for loop' to generate all possible ordered pairs (i, j) where i and j range from 1 to 3, excluding pairs where i == j. Explain how the loop structure enforces these constraints and how to optimize it for larger ranges.",
        "4min":
          "Demonstrate how to iterate over a very large dataset (e.g., millions of records) efficiently without loading it entirely into memory. Implement a generator-based 'for loop' example and explain how Python's iteration protocol and lazy evaluation help manage performance and memory usage.",
      },
    },
    {
      topic: "Algorithms",
      subcategories: {
        "1min":
          "Explain in one or two sentences what an algorithm is, using an everyday comparison.",
        "2min":
          "Describe the steps of an algorithm people use in daily life, like tying shoes or searching for a book, and explain why it counts as an algorithm.",
        "4min":
          "Present pseudocode for a simple algorithm, such as finding the largest number in a list, and explain each step clearly.",
      },
    },
    {
      topic: "Iteration/Recursion",
      subcategories: {
        "1min":
          "Define iteration and recursion in one sentence each, and explain how they differ.",
        "2min":
          "Show one example of iteration (like a loop) and one example of recursion (like factorial), explaining both briefly.",
        "4min":
          "Demonstrate both an iterative and recursive version of a program that sums numbers from 1 to N, and explain how each one works.",
      },
    },
  ],
};
