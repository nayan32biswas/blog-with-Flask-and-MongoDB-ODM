import typer
from mongodb_odm import apply_indexes

app = typer.Typer()


@app.command()
def create_indexes() -> None:
    apply_indexes()


# @app.command()
# def populate_data(
#     total_user: int = typer.Option(10),
#     total_post: int = typer.Option(10),
# ) -> None:
#     from app.tests.data import populate_dummy_data

#     populate_dummy_data(total_user=total_user, total_post=total_post)


# @app.command()
# def delete_data() -> None:
#     from app.tests.data import clean_data

#     clean_data()
