#include "pch.hpp"

#include "Console/LineEditor.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    constexpr auto UP = "\x1B[A"sv;
    constexpr auto DOWN = "\x1B[B"sv;
    constexpr auto RIGHT = "\x1B[C"sv;
    constexpr auto LEFT = "\x1B[D"sv;
    constexpr auto HOME = "\x1B[H"sv;
    constexpr auto END = "\x1B[F"sv;
    constexpr auto DELETE_KEY = "\x1B[3~"sv;
    constexpr auto BACKSPACE = "\x7F"sv;

    std::string Keys(std::initializer_list<std::string_view> keys)
    {
        auto text = std::string{};
        for (const auto key : keys)
        {
            text += key;
        }

        return text;
    }
}

TEST_CASE("LineEditor enters what was typed", "[LineEditor]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("hel").empty());
    CHECK(editor.GetLine() == "hel");
    CHECK(editor.Render() == "\r\x1B[2K> hel");

    CHECK(editor.Feed("p\r") == std::vector<std::string>{"help"});
    CHECK(editor.GetLine().empty());
    CHECK(editor.Render() == "\r\x1B[2K> ");

    // \r\n is one Enter, and each of \r and \n alone is one too.
    CHECK(editor.Feed("status\r\nquit\n\r") == std::vector<std::string>{"status", "quit", ""});
}

TEST_CASE("LineEditor edits in the middle of the line", "[LineEditor]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed(Keys({"stats", LEFT, "u"})).empty());
    CHECK(editor.GetLine() == "status");
    CHECK(editor.GetCursor() == 5);
    CHECK(editor.Render() == "\r\x1B[2K> status\x1B[1D");

    CHECK(editor.Feed(Keys({HOME, DELETE_KEY, "S", END, BACKSPACE, "s", "\x1BOH", RIGHT})).empty());
    CHECK(editor.GetLine() == "Status");
    CHECK(editor.GetCursor() == 1);

    CHECK(editor.Feed("\x0B").empty());
    CHECK(editor.GetLine() == "S");
    CHECK(editor.Feed(Keys({"tatus", LEFT, LEFT, "\x15"})).empty());
    CHECK(editor.GetLine() == "us");
    CHECK(editor.GetCursor() == 0);

    // Keys it doesn't know, such as Ctrl+Right and F5, and other control characters, do nothing.
    CHECK(editor.Feed("\x1B[1;5C\x1B[15~\t\x02").empty());
    CHECK(editor.GetLine() == "us");
    CHECK(editor.GetCursor() == 0);
}

TEST_CASE("LineEditor keeps UTF-8 characters whole", "[LineEditor]")
{
    auto editor = LineEditor{};
    // A character split between reads waits for the rest.
    CHECK(editor.Feed("caf\xC3").empty());
    CHECK(editor.GetLine() == "caf");
    CHECK(editor.Feed("\xA9!").empty());
    CHECK(editor.GetLine() == "caf\xC3\xA9!");

    CHECK(editor.Feed(Keys({LEFT, LEFT})).empty());
    CHECK(editor.GetCursor() == 3);
    CHECK(editor.Render() == "\r\x1B[2K> caf\xC3\xA9!\x1B[2D");
    CHECK(editor.Feed(Keys({DELETE_KEY})).empty());
    CHECK(editor.GetLine() == "caf!");
}

TEST_CASE("LineEditor waits for the rest of a split escape sequence", "[LineEditor]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("ab\x1B").empty());
    CHECK(editor.Feed("[").empty());
    CHECK(editor.GetLine() == "ab");
    CHECK(editor.Feed("Dc").empty());
    CHECK(editor.GetLine() == "acb");

    // A lone Escape does nothing to the key after it.
    CHECK(editor.Feed("\x1Bx").empty());
    CHECK(editor.GetLine() == "acxb");
}

TEST_CASE("LineEditor goes back through the lines entered", "[LineEditor]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("help\rstatus\rstatus\r\r") == std::vector<std::string>{"help", "status", "status", ""});
    CHECK(editor.Feed("dra").empty());

    CHECK(editor.Feed(Keys({UP})).empty());
    CHECK(editor.GetLine() == "status");
    CHECK(editor.Feed(Keys({UP})).empty());
    CHECK(editor.GetLine() == "help");
    CHECK(editor.Feed(Keys({UP})).empty());
    CHECK(editor.GetLine() == "help");

    CHECK(editor.Feed(Keys({DOWN, DOWN})).empty());
    CHECK(editor.GetLine() == "dra");
    CHECK(editor.Feed(Keys({DOWN, "ft"})).empty());
    CHECK(editor.GetLine() == "draft");

    // A recalled line can be changed and entered without changing the one it came from.
    CHECK(editor.Feed(Keys({UP, UP, " me\r"})) == std::vector<std::string>{"help me"});
    CHECK(editor.Feed(Keys({UP})).empty());
    CHECK(editor.GetLine() == "help me");
    CHECK(editor.Feed(Keys({UP, UP})).empty());
    CHECK(editor.GetLine() == "help");
}

TEST_CASE("LineEditor keeps at most MAX_HISTORY lines", "[LineEditor]")
{
    auto editor = LineEditor{};
    for (auto i = std::size_t{0}; i <= LineEditor::MAX_HISTORY; ++i)
    {
        CHECK(editor.Feed(std::to_string(i) + "\r").size() == 1);
    }

    for (auto i = std::size_t{0}; i < LineEditor::MAX_HISTORY + 5; ++i)
    {
        CHECK(editor.Feed(UP).empty());
    }

    CHECK(editor.GetLine() == "1");
}

TEST_CASE("LineEditor buffers multibyte characters across every byte boundary", "[LineEditor][ConsoleCoverage]")
{
    const auto character = std::string{GENERATE("\xC3\xA9", "\xE2\x82\xAC", "\xF0\x9F\x98\x80")};
    auto editor = LineEditor{};
    CHECK(editor.Feed("a").empty());
    for (auto i = std::size_t{0}; i < character.size(); ++i)
    {
        CHECK(editor.Feed(std::string_view{character}.substr(i, 1)).empty());
        CHECK(editor.GetLine() == (i + 1 == character.size() ? "a" + character : "a"));
    }
    CHECK(editor.Feed("!").empty());
    CHECK(editor.Feed(Keys({LEFT, LEFT})).empty());
    CHECK(editor.GetCursor() == 1);
    CHECK(editor.Render() == "\r\x1B[2K> a" + character + "!\x1B[2D");
    CHECK(editor.Feed(RIGHT).empty());
    CHECK(editor.GetCursor() == 1 + character.size());
    CHECK(editor.Feed(BACKSPACE).empty());
    CHECK(editor.GetLine() == "a!");
    CHECK(editor.GetCursor() == 1);
}

TEST_CASE("LineEditor deletes multibyte characters without consuming adjacent text", "[LineEditor][ConsoleCoverage]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("a\xE2\x82\xAC" "b\xF0\x9F\x98\x80").empty());
    CHECK(editor.Feed(Keys({HOME, RIGHT, DELETE_KEY})).empty());
    CHECK(editor.GetLine() == "ab\xF0\x9F\x98\x80");
    CHECK(editor.GetCursor() == 1);
    CHECK(editor.Feed(Keys({RIGHT, DELETE_KEY})).empty());
    CHECK(editor.GetLine() == "ab");
    CHECK(editor.GetCursor() == 2);
}

TEST_CASE("LineEditor recognises alternate home and end keys", "[LineEditor][ConsoleCoverage]")
{
    const auto home = GENERATE("\x01", "\x1B[1~", "\x1B[7~", "\x1BOH");
    const auto end = GENERATE("\x05", "\x1B[4~", "\x1B[8~", "\x1BOF");
    auto editor = LineEditor{};
    CHECK(editor.Feed("abc").empty());
    CHECK(editor.Feed(home).empty());
    CHECK(editor.GetCursor() == 0);
    CHECK(editor.Feed("<").empty());
    CHECK(editor.Feed(end).empty());
    CHECK(editor.GetCursor() == 4);
    CHECK(editor.Feed(">").empty());
    CHECK(editor.GetLine() == "<abc>");
}

TEST_CASE("LineEditor editing keys do nothing at empty line boundaries", "[LineEditor][ConsoleCoverage]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed(Keys({LEFT, RIGHT, BACKSPACE, DELETE_KEY, UP, DOWN, "\b\x0B\x15"})).empty());
    CHECK(editor.GetLine().empty());
    CHECK(editor.GetCursor() == 0);
    CHECK(editor.Feed("a").empty());
    CHECK(editor.Feed(Keys({RIGHT, DELETE_KEY})).empty());
    CHECK(editor.GetLine() == "a");
    CHECK(editor.Feed(Keys({HOME, LEFT, BACKSPACE})).empty());
    CHECK(editor.GetLine() == "a");
    CHECK(editor.GetCursor() == 0);
}

TEST_CASE("LineEditor drops stray continuation and invalid leading bytes", "[LineEditor][ConsoleCoverage]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("\x80\xBF\xF8\xFF\t\x02").empty());
    CHECK(editor.GetLine().empty());
    CHECK(editor.Feed("ok\n") == std::vector<std::string>{"ok"});
}

TEST_CASE("LineEditor discards oversized unfinished escapes and resumes typing", "[LineEditor][ConsoleCoverage]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("safe\x1B[").empty());
    CHECK(editor.Feed(std::string(13, '1')).empty());
    CHECK(editor.GetLine() == "safe");
    CHECK(editor.Feed("1").empty());
    CHECK(editor.Feed(" text\n") == std::vector<std::string>{"safe text"});
}

TEST_CASE("LineEditor treats split CRLF as one enter and retains the following line", "[LineEditor][ConsoleCoverage]")
{
    auto editor = LineEditor{};
    CHECK(editor.Feed("one\r") == std::vector<std::string>{"one"});
    CHECK(editor.Feed("").empty());
    CHECK(editor.Feed("\nsecond").empty());
    CHECK(editor.GetLine() == "second");
    CHECK(editor.Feed("\n") == std::vector<std::string>{"second"});
    CHECK(editor.Feed("\n") == std::vector<std::string>{""});
}

TEST_CASE("LineEditor renders entered text without leaving a cursor offset", "[LineEditor][ConsoleCoverage]")
{
    CHECK(LineEditor::RenderEntered("hello") == "\r\x1B[2K> hello\r\n");
    CHECK(LineEditor::RenderEntered("") == "\r\x1B[2K> \r\n");
    CHECK(LineEditor::Erase() == "\r\x1B[2K");
}
