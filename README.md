# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/IvanAnishchuk/geek42/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|--------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/geek42/\_\_init\_\_.py       |       13 |        0 |        0 |        0 |    100% |           |
| src/geek42/\_\_main\_\_.py       |        2 |        2 |        0 |        0 |      0% |       1-3 |
| src/geek42/blog.py               |       44 |        0 |       14 |        0 |    100% |           |
| src/geek42/cli.py                |      412 |      173 |      162 |       11 |     54% |67, 74-77, 102-103, 117, 151-\>161, 158-159, 193, 312-314, 334, 352-\>exit, 382-\>exit, 396, 415-422, 470-484, 496-509, 523-526, 536-572, 577-590, 607-646, 654-658, 666-742, 747-751 |
| src/geek42/compose.py            |       95 |        4 |       26 |        2 |     95% |37, 47, 110-111, 236-\>233 |
| src/geek42/errors.py             |       53 |        0 |        0 |        0 |    100% |           |
| src/geek42/feeds.py              |       65 |        0 |        8 |        0 |    100% |           |
| src/geek42/linter.py             |      118 |        6 |       58 |        3 |     95% |62-65, 74-\>87, 124, 167 |
| src/geek42/manifest.py           |       36 |        2 |        8 |        2 |     91% |    69, 92 |
| src/geek42/models.py             |       36 |        0 |        0 |        0 |    100% |           |
| src/geek42/parser.py             |       60 |        2 |       22 |        6 |     90% |36-\>45, 41-\>36, 61-\>69, 115, 118, 119-\>113 |
| src/geek42/renderer.py           |       31 |        0 |        8 |        1 |     97% |   34-\>36 |
| src/geek42/scaffold.py           |       30 |        0 |        6 |        1 |     97% |   23-\>26 |
| src/geek42/site.py               |       71 |        0 |       26 |        2 |     98% |71-\>73, 125-\>128 |
| src/geek42/tracker.py            |       27 |        0 |        4 |        0 |    100% |           |
| src/pyscv/\_\_init\_\_.py        |        0 |        0 |        0 |        0 |    100% |           |
| src/pyscv/config.py              |       74 |        0 |       22 |        0 |    100% |           |
| src/pyscv/download\_artifacts.py |      165 |        0 |       52 |        0 |    100% |           |
| src/pyscv/download\_proofs.py    |      266 |        0 |       92 |        0 |    100% |           |
| src/pyscv/net.py                 |       62 |        0 |       18 |        0 |    100% |           |
| **TOTAL**                        | **1660** |  **189** |  **526** |   **28** | **86%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/IvanAnishchuk/geek42/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/IvanAnishchuk/geek42/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/IvanAnishchuk/geek42/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/IvanAnishchuk/geek42/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FIvanAnishchuk%2Fgeek42%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/IvanAnishchuk/geek42/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.