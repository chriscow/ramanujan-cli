import click        # command line tools
import commands
import nsq
import dotenv

@click.group()
def cli():
    pass

if __name__ == '__main__':
    dotenv.load_dotenv()
    cli.add_command(commands.spawn)
    cli.add_command(commands.generate)
    cli.add_command(commands.slowgen)
    cli.add_command(commands.search)
    cli()

