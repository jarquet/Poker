#!/usr/bin/env python3
"""
2-Player Texas Hold'em Poker Game
Main entry point for the CLI poker game
"""

from cli import CLI


def main():
    """Main entry point"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()

