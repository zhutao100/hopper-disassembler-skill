<span id="search_expr"></span>

# Hexadecimal Regular Expressions

Hopper can search for a given pattern in the bytes of a disassembled file. In order to proceed, Hopper uses a small language, very similar to regular expressions seen in tools like *grep*.

Regular expressions are made of words, using letters from the alphabet **0123456789abcdef**, and special characters like **\***, **+**, **?**, **.**, **\|**, and parenthesis. From a regular expression, Hopper will build a *deterministic finite automaton*, and use it to search the pattern in the file. Each byte of the file is split into two 4-bits words, and given to the automaton.

- Letters from the **0123456789abcdef** alphabet are used *as is*,

- The special character **.** matches any 4-bit word. If you want to match with any byte, you should use the **..** sequence,

- The character **\*** is used to indicate that the previous word can be repeated 0, or more times. Please note that this character applies to the whole word, not only the last character, or byte. For instance, the regular expression:

      123*abc*123

  matches the strings:

  - 123abc123
  - 123123123abcabc123
  - abc123
  - …

- You can restrict the effect of the star by using some parenthesis. For instance, in the regular expression:

      12345(ab*)678

  only the word **ab** is repeated.

- You can specify a subset of characters, using the square brackets:

      [168ab]

  Will match if the word is 1, 6, 8, a, or b. You can also provide ranges:

      [2-8cd]

  Will match if the word is 2, 3, 4, 5, 6, 7, 8, c, or d.

- As a shortcut, you can use the character **+** as a way to represent 1, or more occurences of the pattern.

- Another shortcut is the character **?**, which mean 0, or 1 occurrence of the pattern.

- You can combine two regular expressions using a *logical or* with the character **\|**. For instance:

      AB|CD

  Will match words AB, or CD.

## Some examples

- A sequence beginning with **12**, and ending with **ab**:

      12(..*)ab

- A NULL-terminated string of decimal characters:

      3[0-9]+00

- Roughly match all the instructions **xor al,al**, **xor ax,ax**, **xor eax,eax**, and **xor rax,rax**

      (48|66)?(30|31)C0
