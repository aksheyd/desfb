#include <cstdlib>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

using namespace std;

void command_screen();
void DESFB_overview();
void modeler_main();
void instructions();
void change_climate(int input);

// Prefer venv python if present; otherwise system python3.
static string python_cmd() {
    if (system("test -x .venv/bin/python") == 0) {
        return ".venv/bin/python";
    }
    return "python3";
}

static void run_python_scripts(int temp_f) {
    string py = python_cmd();
    string analyze = py + " sheet_analyzer.py -p " + to_string(temp_f);
    string printit = py + " print_data.py";
    system("clear && printf '\\e[3J'");
    system(analyze.c_str());
    system("clear && printf '\\e[3J'");
    system(printit.c_str());
}

int main() {
    int input;

    system("clear && printf '\\e[3J'");
    cout << "Welcome to the Don Edwards San Fransisco Bay Wildlife Refuge Climate Modeler" << endl;
    cout << "Please choose an option from below:" << endl;
    cout << "1: Start" << endl;
    cout << "2: Quit" << endl;

    while (cin >> input) {
        if (input == 1) {
            DESFB_overview();
            break;
        } else if (input == 2) {
            break;
        } else {
            command_screen();
        }
    }
    return 0;
}

void command_screen() {
    cout << "Incorrect input selected, please try again:" << endl;
    cout << "1: Start" << endl;
    cout << "2: Quit" << endl;
}

void DESFB_overview() {
    system("clear && printf '\\e[3J'");
    string input;

    cout << "Don Edwards San Francisco Bay National Wildlife Refuge, CA, USA" << endl;
    cout << "===============================================================" << endl << endl;

    cout << "Habitats: Marsh, Ponds, Mudflat, Vernal Pools, Uplands" << endl;
    cout << "Species: 269 Birds, 28 Mammals, 12 Amphibian/Reptiles, 62 Fish, 335 Fauna" << endl;
    cout << endl;

    this_thread::sleep_until(chrono::system_clock::now() + chrono::seconds(1));
    system("clear && printf '\\e[3J'");

    cout << "Here's a sneakpeek at some of the birds, mammals, etc" << endl;
    cout << "For the Danger Level column, this number is calculated based on the initial data given" << endl <<
            "from the US Fish & Wildlife Service. It is based on many factors including the species" << endl <<
            "origin, endangered-level, etc." << endl;
    cout << "(Toy heuristic — not a scientific extinction model.)" << endl;

    this_thread::sleep_until(chrono::system_clock::now() + chrono::seconds(1));

    run_python_scripts(60);

    cout << "Please click enter when you are ready to move on!" << endl;
    cin >> input;

    modeler_main();
}

void modeler_main() {
    system("clear && printf '\\e[3J'");

    int input;
    cout << "Now, it's your turn! Use the following instructions to affect the climate:" << endl << endl;
    instructions();
    cin >> input;

    while (input < 0 || input > 99) {
        cout << "Error: incorrect input detected." << endl;
        instructions();
        cin >> input;
    }

    change_climate(input);
}

void instructions() {
    cout << "Input a temperature from 0 to 99 degrees Fahrenheit." << endl;
    cout << "Ex: 50, 95, 99, 5, etc." << endl;
}

void change_climate(int input) {
    run_python_scripts(input);

    int hel;
    cin >> hel;
}
