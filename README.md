# top4grep
A grep tool for the top 4 security conferences

## Installation
```
git clone https://github.com/Kyle-Kyle/top4grep
cd top4grep
pip3 install .
```

## Usage 
### Database Initialization
If you want to update the papers stored in `top4grep/papers.db`, you can recreate it with:
```bash
top4grep --build-db --abstracts
```

Make sure to install the database build requirements too when building/updating the database: `pip3 install .[BUILD]`.

### Query
```bash
top4grep -r <regexps>
```

For example, `python top4grep.py -r linux|kernel`
Currently, the query is a regexp. If you want to `and` concatenate multiple regexp you can do this via `#`, i.e., "linux#kernel" only matches title/abstracts where both words are contained.

Add `--abstracts` to consider and print the abstracts too.

## Screenshot
![screenshot](https://raw.githubusercontent.com/Kyle-Kyle/top4grep/master/img/screenshot.png)
