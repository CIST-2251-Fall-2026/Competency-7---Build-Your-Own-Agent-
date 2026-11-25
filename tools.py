import ast
import operator

from retrieval import load_documents, split_documents, search_documents

documents = load_documents()
chunks = split_documents(documents)

# Tool 1: Search NASA articles
def search_nasa(query):
    results = search_documents(query, chunks)

    return [
        {
            "source": result["name"],
            "text": result["text"]
        }
        for result in results
    ]

# Tool 2: Calculator
def calculator(expression):
    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv
    }

    def calculate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](
                calculate(node.left),
                calculate(node.right)
            )

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -calculate(node.operand)

        raise ValueError("Unsupported calculation")

    try:
        tree = ast.parse(expression, mode="eval")
        return calculate(tree.body)
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as error:
        return f"Calculation error: {error}"


# Tool 3: Compare two planets
def compare_planets(planet1, planet2):
    first = search_nasa(planet1)
    second = search_nasa(planet2)

    return {
        planet1: first,
        planet2: second
    }


# Tool 4: Get a specific NASA article
def get_source(name):
    for document in documents:
        if document["name"].lower() == name.lower():
            return document["text"][:3000]

    return "Source not found."


if __name__ == "__main__":
    print("Testing NASA search:")
    print(search_nasa("Mars orbit"))

    print("\nTesting calculator:")
    print(calculator("365 * 2"))

    print("\nTesting planet comparison:")
    print(compare_planets("Earth", "Mars"))

    print("\nTesting NASA source:")
    print(get_source("jupiter")[:300])