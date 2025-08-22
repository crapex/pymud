TRANSLATION = {
    "text" : {
        "welcome"           : "Welcome to PYMUD Client - PKUXKX, the best Chinese MUD game",  # the welcome text shown in the statusbar when pymud start

        # text in pymud.py
        "world"             : "World",                                                        # the display text of menu "world"
        "new_session"       : "Create New Session",                                           # the display text of sub-menu "new_session"
        "show_log"          : "Show Log Information",                                         # the display text of sub-menu "show_log"                          
        "exit"              : "Exit",                                                         # the display text of sub-menu "exit"
        "session"           : "Session",                                                      # the display text of menu "session"
        "connect"           : "Connect/Reconnect",                                            # the display text of sub-menu "connect"
        "disconnect"        : "Disconnect",                                                   # the display text of sub-menu "disconnect"
        "beautify"          : "Toggle Beautify Display",                                      # the display text of sub-menu "toggle beautify"
        "echoinput"         : "Toggle Echo Input Commands",                                   # the display text of sub-menu "toggle echo input"
        "nosplit"           : "Disable Split Screen",                                         # the display text of sub-menu "no split"   
        "copy"              : "Copy (Plain Text)",                                            # the display text of sub-menu "copy (pure text)"
        "copyraw"           : "Copy (ANSI)",                                                  # the display text of sub-menu "copy (raw infomation)"                      
        "clearsession"      : "Clear Session Content",                                        # the display text of sub-menu "clear session buffer"
        "closesession"      : "Close Current Page",                                           # the display text of sub-menu "close current session"
        "autoreconnect"     : "Toggle Auto Reconnect",                                        # the display text of sub-menu "toggle auto reconnect"
        "loadconfig"        : "Load Script Configuration",                                    # the display text of sub-menu "load config"
        "reloadconfig"      : "Reload Script Configuration",                                  # the display text of sub-menu "reload config"
        "layout"            : "Layout",                                                       # the display text of menu "layout" (not used now)
        "hide"              : "Hide Status Window",                                           # the display text of sub-menu "hide status window" (not used now)
        "horizon"           : "Bottom Status Window",                                         # the display text of sub-menu "horizon layout" (not used now)
        "vertical"          : "Right Status Window",                                          # the display text of sub-menu "vertical layout" (not used now)
        "help"              : "Help",                                                         # the display text of menu "help"
        "about"             : "About",                                                        # the display text of menu "about"

        "session_changed"   : "Successfully switched to session: {0}",
        "input_prompt"      : '<prompt><b>Command:</b></prompt>', 
        "msg_copy"          : "Copied: {0}",
        "msg_copylines"     : "Copied: {0} lines",
        "msg_no_selection"  : "No content selected...",
        "msg_session_exists" : "Error! A session named {0} already exists, please try another name.",

        "logfile_name"      : "Log File Name",
        "logfile_size"      : "File Size",
        "logfile_modified"  : "Last Modified Time",

        "warning"           : "Warning",
        "warning_exit"      : "Application Exit Warning",
        "session_close_prompt" : "Session {0} is still connected, confirm to close?",
        "app_exit_prompt"   : "There are still {0} sessions {1} connected, confirm to close?",

        "msg_beautify"      : "Beautify display is now",
        "msg_echoinput"     : "Echo input commands is set to:",
        "msg_autoreconnect" : "Auto reconnect is set to:",
        "msg_open"          : "On",
        "msg_close"         : "Off",

        "msg_cmd_session_error" : 'When creating a session with a single parameter, use the format group.name, e.g. #session pkuxkx.newstart',
        "msg_cmdline_input" : "Command line input:",
        "msg_no_session"    : "No active session currently running.",
        "msg_invalid_plugins"   : "File: {0} is not a valid plugin file, loading error, message: {1}",

        "status_nobeautify" : "Beautify disabled",
        "status_mouseinh"   : "Mouse disabled",
        "status_ignore"     : "Global disable",
        "status_notconnect" : "Not connected",
        "status_connected"  : "Connected",

        # text in dialogs.py
        "basic_dialog"      : "Basic Dialog",
        "ok"                : "OK",
        "cancel"            : "Cancel",
        "visit"             : "Visit",
        "displayhelp"       : "to view the latest help documentation",
        "appinfo"           : '<b fg="red">PYMUD {0}</b> - a MUD Client Written in Python',
        "author"            : 'Author: <b>{0}</b> <b>E-mail</b>: <u>{1}</u>',
        "sysversion"        : 'System:{} {}   Python Version:{}',
        "sessionname"       : "Session Name",
        "host"              : "Server Address",
        "port"              : "Port",
        "encoding"          : "Encoding",
        "nolog"             : "No Log",
        "chooselog"         : "Select Log to View",

        # text in modules.py
        "configuration_created"    : "Configuration object {0}.{1} created successfully.",
        "configuration_recreated"  : "Configuration object {0}.{1} recreated successfully.",
        "configuration_fail"       : "Configuration object {0}.{1} creation failed. Error message: {}",
        "entity_module"            : "Main Configuration Module",
        "non_entity_module"        : "Sub Configuration Module",
        "load_ok"                  : "Load completed",
        "load_fail"                : "Load failed",
        "unload_ok"                : "Unload completed",
        "reload_ok"                : "Reload completed",
        "msg_plugin_unloaded"      : "Plugin {0} has been disabled for this session.",
        "msg_plugin_loaded"        : "Plugin {0} has been enabled for this session.",

        # text in objects.py
        "excpetion_brace_not_matched"   : "Invalid code block, number of braces does not match",
        "exception_quote_not_matched"   : "Number of quotes does not match",
        "exception_forced_async"        : "This command contains both forced synchronous and asynchronous commands, will use asynchronous execution, synchronous commands will be invalid.",
        "exception_session_type_fail"   : "session must be an instance of Session type object!",
        "exception_message"             : "Exception information: <{}> {}",
        "exception_traceback"           : "Exception occurred at line number {1} in file '{0}', and function name is '{2}'",
        "script_error"                  : "Script Error",

        # text display in session.py
        "msg_var_autoload_success"      : "Variables automatically loaded from {0} successfully.",
        "msg_var_autoload_fail"         : "Failed to automatically load variables from {0}, error message: {1}.",
        "msg_auto_script"               : "Will automatically load the following modules: {0}",
        "msg_connection_fail"           : "Error occurred during connection creation, time: {0}, error message: {1}.",
        "msg_auto_reconnect"            : "Will automatically reconnect in {0} seconds...",
        "msg_connected"                 : "{0}: Successfully connected to server.",
        "msg_disconnected"              : "{0}: Disconnected from server.",
        "msg_duplicate_logname"         : "A logger named {0} already exists in other sessions, will return this logger directly.",
        "msg_default_statuswindow"      : "This is a default status window message\nSession: {0} Connection Status: {1}",
        "msg_mxp_not_support"           : "MXP support is not yet developed, please do not enable MXP support settings for now!",
        "msg_no_session"                : "No session named {0} exists.",
        "msg_num_positive"              : "#{num} {cmd} only supports positive integers!",
        "msg_cmd_not_recognized"        : "Unrecognized command: {0}",
        "msg_id_not_consistent"         : "Object {0} dictionary key {1} does not match its id {2}, will discard key and add to session using its id...",
        "msg_shall_be_string"           : "{0} must be string type",
        "msg_shall_be_list_or_tuple"    : "{0} names should be tuple or list, other types not accepted",
        "msg_names_and_values"           : "names and values should not be empty and have equal length",
        "msg_not_null"                  : "{0} cannot be null",
        "msg_topic_not_found"           : "Topic {0} not found, please confirm input is correct.",
        "Day"                           : "Day",
        "Hour"                          : "Hour",
        "Minute"                        : "Minute",
        "Second"                        : "Second",
        "msg_connection_duration"       : "Connected to server for: {0}",
        "msg_no_object"                 : "No {1} named {0} exists in current session.",
        "msg_no_global_object"          : "No {1} named {0} exists in global space.",
        "msg_object_value_setted"       : "Successfully set {0} {1} value to {2}.",
        "variable"                      : "variable",
        "globalvar"                     : "global variable",
        "msg_object_not_exists"         : "No {1} with key {0} exists in current session, please confirm and try again.",
        "msg_object_enabled"            : "Object {0} enabled status is now on.",
        "msg_object_disabled"           : "Object {0} enabled status is now off.",
        "msg_object_deleted"            : "Object {0} has been deleted from session.",
        "msg_group_objects_enabled"     : "{1} object(s) of Type {2} in group {1} has(have) been enabled.",
        "msg_group_objects_disabled"    : "{1} object(s) of Type {2} in group {1} has(have) been disabled.",
        "msg_group_objects_deleted"     : "{1} object(s) of Type {2} in group {1} has(have) been deleted.",
        "msg_object_param_invalid"      : "#{0} command's second parameter only accepts on/off/del",
        "msg_ignore_on"                 : "All trigger enables are globally disabled.",
        "msg_ignore_off"                : "No longer globally disable all trigger enables.",
        "msg_T_plus_incorrect"          : "#T+ enable group usage incorrect, correct usage example: #t+ mygroup \nPlease use #help ignore for query.",
        "msg_T_minus_incorrect"         : "#T- disable group usage incorrect, correct usage example: #t- mygroup \nPlease use #help ignore for query.",
        "msg_group_enabled"             : "Group {0}: {1} aliases, {2} triggers, {3} commands, {4} timers, {5} GMCP triggers are all enabled.",
        "msg_group_disabled"            : "Group {0}: {1} aliases, {2} triggers, {3} commands, {4} timers, {5} GMCP triggers are all disabled.",
        "msg_repeat_invalid"            : "Current session is not connected or no command has been entered, repeat invalid",
        "msg_window_title"              : "Message from session {0}",
        "msg_module_load_fail"          : "Module {0} load failed, exception: {1}, type: {2}.",
        "msg_exception_traceback"       : "Exception traceback: {0}",
        "msg_module_not_loaded"         : "Specified module name {0} is not loaded.",
        "msg_all_module_reloaded"       : "All configuration modules reloaded successfully.",
        "msg_plugins_reloaded"          : "Plugin {0} reloaded successfully.",
        "msg_name_not_found"            : "Specified name {0} neither found as module nor plugin, reload failed...",
        "msg_no_module"                 : "No modules loaded in current session.",
        "msg_module_list"               : "Current session has loaded {0} modules, including (in loading order): {1}.",
        "msg_module_configurations"     : "Module {0} contains configurations: {1}.",
        "msg_submodule_no_config"       : "Module {0} is a submodule, contains no configurations.",
        "msg_module_not_loaded"         : "No module named {0} exists in this session, may not be loaded to this session yet.",
        "msg_variables_saved"           : "Session variable information saved to {0}.",
        "msg_alias_created"             : "Alias {0} created successfully: {1}",
        "msg_trigger_created"           : "Trigger {0} created successfully: {1}",
        "msg_timer_created"             : "Timer {0} created successfully: {1}",
        
        "msg_tri_triggered"             : "    {0} triggered normally.",
        "msg_tri_wildcards"             : "      Captured: {0}",
        "msg_tri_prevent"               : "      {0}This trigger does not have keepEval enabled, will prevent subsequent triggers.{1}",
        "msg_tri_ignore"                : "    {1}{0} can trigger, but due to priority and keepEval settings, trigger will not activate.{2}",
        "msg_tri_matched"               : "    {0} can match trigger.",
        "msg_enabled_summary_0"         : "{0}  Among enabled triggers, none can trigger.",
        "msg_enabled_summary_1"         : "{0}  Among enabled triggers, {1} can trigger, actually triggered {2}, another {3} will not activate due to keepEval.",
        "msg_enabled_summary_2"         : "{0}  Among enabled triggers, all {1} can trigger normally.",
        "msg_disabled_summary_0"        : "{0}  Among disabled triggers, {1} can match.",
        "msg_disabled_summary_1"        : "{0}  Disabled triggers, none can match.",
        "msg_test_summary_0"            : "  Test content: {0}",
        "msg_test_summary_1"            : "  Test result: No matching triggers.",
        "msg_test_summary_2"            : "  Test result: {0} triggers can trigger normally, total {1} satisfy matching requirements.",
        "msg_test_title"                : "Trigger Test - {0}",
        "msg_triggered_mode"            : "'Response Mode'",
        "msg_matched_mode"              : "'Test Mode'",

        "msg_no_plugins"                : "PYMUD currently has no plugins loaded.",
        "msg_plugins_list"              : "PYMUD currently has {0} plugins loaded, respectively:",
        "msg_plugins_info"              : "Author {2} Version {1}  Release Date {3}\n  Description: {0}",

        "msg_py_exception"              : "Python execution error: {0}",

        "title_msg"                     : "Message",
        "title_warning"                 : "Warning",
        "title_error"                   : "Error",
        "title_info"                    : "Info",

        "msg_log_title"                 : "Logger status in this session:",
        "msg_log_title2"                : "Logger status in other sessions of this application:",
        "logger"                        : "Logger",
        "enabled"                       : "Enabled",
        "disabled"                      : "Disabled",
        "logger_status"                 : "Current Status",
        "file_mode"                     : "File Mode",
        "logger_mode"                   : "Log Mode",
        "ANSI"                          : "ANSI",
        "plain_text"                    : "Plain Text",

        "filemode_new"                  : "New",
        "filemode_append"               : "Append",
        "filemode_overwrite"            : "Overwrite",

        "msg_logger_enabled"            : "{0}: Logger {1} enabled with {2} file mode and {3} log mode.",
        "msg_logger_disabled"           : "{0}: Logger {1} logging disabled.",
        "msg_logfile_not_exists"        : "Specified log file {0} does not exist.",

        "exception_logmode_error"       : "Invalid log mode: {0}",
        "exception_plugin_file_not_found"   : "Specified plugin file {0} does not exist or format is incorrect.",
    },

    "docstring" : {
        "PyMudApp": {
            "handle_session" :
        '''
        The execution function of the embedded command #session, used to create a remote connection session.
        This function should not be called directly in the code.

        Usage:
            - #session {name} {host} {port} {encoding}
            - When Encoding is not specified, the default encoding is utf-8.
            - You can directly use #{name} to switch sessions and operate session commands.

            - #session {group}.{name}
            - This is equivalent to directly clicking the {name} menu under the {group} menu to create a session. If the session already exists, switch to that session.

        Parameters:
            :name: Session name
            :host: Server domain name or IP address
            :port: Port number
            :encoding: Encoding format. If not specified, the default is utf8.
    
            :group: Group name, which is a keyword under the sessions field in the configuration file.
            :name: Shortcut name for the session, which is a keyword under the chars field of the above group keyword.

        Examples:
            ``#session {name} {host} {port} {encoding}`` 
                Create a remote connection session, connect to the specified port of the remote host using the specified encoding format, and save it as {name}. The encoding can be omitted, in which case the value of Settings.server["default_encoding"] will be used, with a default of utf8.
            ``#session newstart mud.pkuxkx.net 8080 GBK`` 
                Connect to port 8080 of mud.pkuxkx.net using GBK encoding, and name the session newstart.
            ``#session newstart mud.pkuxkx.net 8081`` 
                Connect to port 8081 of mud.pkuxkx.net using UTF8 encoding, and name the session newstart.
            ``#newstart`` 
                Switch the session named newstart to the current session.
            ``#newstart give miui gold`` 
                Make the session named newstart execute the "give miui gold" command without switching to that session.

            ``#session pkuxkx.newstart``
                Create a session through the specified shortcut configuration, which is equivalent to clicking the World -> pkuxkx -> newstart menu to create a session. If the session exists, switch to that session.

        Related commands:
            - #close
            - #exit

        ''',


        },
        "Session": {
            "handle_exit" :
        '''
        The execution function of the embedded command #exit, used to exit the `PyMudApp` application.
        This function should not be called directly in the code.

        *Note: When there are sessions still connected in the application, exiting the application with #exit will pop up dialog boxes one by one to confirm whether to close these sessions.*

        Related commands:
            - #close
            - #session
        ''',

            "handle_close" :
        '''
        The execution function of the embedded command #close, used to close the current session and remove it from the session list of `PyMudApp`.
        This function should not be called directly in the code.

        *Note: When the current session is connected, closing the session with #close will pop up a dialog box to confirm whether to close.*

        Related commands:
            - #exit
            - #session
        ''',

            "handle_variable" :
        '''
        The execution function of the embedded command #variable / #var, used to operate session variables.
        This command can be used with no parameters, one parameter, or two parameters.
        This function should not be called directly in the code.

        Usage:
            - #var: List all variables in this session.
            - #var {name}: List the value of the variable named {name} in this session.
            - #var {name} {value}: Set the value of the variable named {name} in this session to {value}, create it if it does not exist.

        Parameters:
            :name: Variable name.
            :value: Variable value. Note: After assignment, this value will be of type str!

        Related commands:
            - #global
        ''',

            "handle_global" :
        '''
        The execution function of the embedded command #global, used to operate global variables.
        This command can be used with no parameters, one parameter, or two parameters.
        This function should not be called directly in the code.

        Usage:
            - #global: List all global variables.
            - #global {name}: List the value of the global variable named {name}.
            - #global {name} {value}: Set the value of the global variable named {name} to {value}, create it if it does not exist.

        Parameters:
            :name: Variable name.
            :value: Variable value. Note: After assignment, this value will be of type str!

        Related commands:
            - #variable
        ''',

            "handle_task" :
        '''
        The execution function of the embedded command #task, used to display all managed task lists (for debugging only).
        This function should not be called directly in the code.

        Note:
            When there are many managed tasks, this command will affect system response.
        ''',

            "handle_ignore" :
        '''
        The execution function of the embedded commands #ignore / #ig, #t+ / #t-, used to handle enable/disable status.
        This function should not be called directly in the code.

        Usage:
            - #ig: Toggle the global enable/disable status of triggers.
            - #t+ [>=]{group}: Enable all objects in the {group} group, including aliases, triggers, commands, timers, GMCP triggers, etc.
            - #t- [>=]{group}: Disable all objects in the {group} group, including aliases, triggers, commands, timers, GMCP triggers, etc.

        Parameters:
            :group: Group name. There could be a '=' or '>' sign before groupname, to indicate only this group or this group and it's subgroups. If there is no sign, it is equavalant to use '='.

        Examples:
            - ``#ig``: Toggle the global enable/disable status of triggers. When disabled, "Global disabled" will be displayed in the lower right corner of the status bar.
            - ``#t+ mygroup``: Enable all objects in the group named mygroup, including aliases, triggers, commands, timers, GMCP triggers, etc.
            - ``#t- mygroup``: Disable all objects in the group named mygroup, including aliases, triggers, commands, timers, GMCP triggers, etc.
            - ``#t+ >mygroup``: Enable all objects in the group named mygroup and its subgroups (eg. mygroup.subgroup, etc.), including aliases, triggers, commands, timers, GMCP triggers, etc.

        Related commands:
            - #trigger
            - #alias
            - #timer
        ''',

            "handle_help" :
        '''
        The execution function of the embedded command #help, used to display help information for the specified topic.
        This function should not be called directly in the code.

        Usage:
            - #help: Display a list of all available commands.
            - #help <topic>: Display help information for the specified topic.

        Examples:
            - #help alias: Display help information for the alias command.
            - #help trigger: Display help information for the trigger command.
        ''',

            "handle_test" :
        '''
        The execution function of the embedded command #test/#show/#echo, trigger testing command. Similar to zmud's #show command.
        This function should not be called directly in the code.

        Usage:
            - #show {some_text}: Test trigger response when receives {some_text}. Triggers won't actually execute.
            - #test {some_text}: Difference from #show is that matched triggers will execute regardless of enabled status.
            - #echo {some_text}: Simulate receiving {some_text} from server, triggers will execute normally but won't display test results.

        Examples:
            - ``#show You take a deep breath and stand up.``: Simulate trigger testing when server receives "You take a deep breath and stand up." (display test results only)
            - ``#test %copy``: Copy a sentence and simulate trigger testing when server receives the copied content again
            - ``#test You take a deep breath and stand up.``: Actual trigger execution will occur even if disabled
            - ``#echo You take a deep breath and stand up.``: Simulate trigger testing when server receives "You take a deep breath and stand up." (won't display test results)

        Notes:
            - #show command only displays test results without actual trigger execution
            - #test command forces actual trigger execution regardless of enabled status
            - #echo command can be used to manually trigger triggers
        ''',

            "handle_timer" :
        '''
        The execution function of embedded command #timer/#ti for timer operations. Can be used with 0-2 parameters.
        This function should not be called directly in the code.

        Usage:
            - #ti: Show all timers in current session
            - #ti {ti_id}: Show details of timer with ID {ti_id}
            - #ti {ti_id} {on/off/del}: Enable/disable/delete timer with ID {ti_id}
            - #ti {second} {code}: Create new timer with interval {second} seconds executing {code}
            - PyMUD supports multiple concurrent timers

        Parameters:
            :ti_id:   Timer ID
            :on:      Enable
            :off:     Disable
            :del:     Delete
            :second:  Interval in seconds for new timer
            :code:    Code to execute when timer triggers
    
        Examples:
            - ``#ti``: List all timers
            - ``#ti my_timer``: Show details of 'my_timer' timer
            - ``#ti my_timer on``: Enable 'my_timer' timer
            - ``#ti my_timer off``: Disable 'my_timer' timer
            - ``#ti my_timer del``: Delete 'my_timer' timer
            - ``#ti 100 {drink jiudai;#wa 200;eat liang}``: Create timer executing drink/eat commands every 100 seconds

        Related commands:
            - #alias
            - #trigger
            - #command
        ''',

            "handle_command" :
        '''
        The execution function of the embedded command #command / #cmd for command operations. Can be used with 0-2 parameters.
        This function should not be called directly in the code.

        Usage:
            - #cmd: Show all commands in current session
            - #cmd {cmd_id}: Show details of command with ID {cmd_id}
            - #cmd {cmd_id} {on/off/del}: Enable/disable/delete command with ID {cmd_id}
            - Commands can only be created through script code due to their special nature

        Parameters:
            :cmd_id: Command ID
            :on: Enable
            :off: Disable
            :del: Delete

        Examples:
            - ``#cmd`` : No parameters, list all commands
            - ``#cmd my_cmd`` : Single parameter, show details of 'my_cmd' command
            - ``#cmd my_cmd on`` : Two parameters, enable 'my_cmd' command
            - ``#cmd my_cmd off`` : Two parameters, disable 'my_cmd' command
            - ``#cmd my_cmd del`` : Two parameters, delete 'my_cmd' command

        Related commands:
            - #alias
            - #trigger
            - #timer
        ''',
            
            "handle_warning" :
        '''
        The execution function of the embedded command #warning, using session.warning to output messages for testing.
        This function should not be called directly in the code.

        Usage:
            - #warning {msg}

        Related commands:
            - #info
            - #error
        ''',

            "handle_error" :
        '''
        The execution function of the embedded command #error, using session.error to output messages for testing.
        This function should not be called directly in the code.

        Usage:
            - #error {msg}

        Related commands:
            - #info
            - #warning
        ''',

            "handle_log" :
        '''
        Execution function for the embedded command #log, controlling the logging status of the current session.
        This function should not be called directly in code.

        Usage:
            - #log : Display status of all loggers
            - #log start [logger-name] [-a|-w|-n] [-r] : Start a logger

                Parameters:
                    - :logger-name: Logger name. When unspecified, uses session name (default session logger)
                    - :-a|-w|-n: File mode selection. 
                      -a Append mode (default), adds to end of existing log file
                      -w Overwrite mode, clears existing file and starts fresh
                      -n New mode, creates timestamped file in name.now.log format
                    - :-r: Enable raw logging mode

            - #log stop [logger-name] : Stop a logger
                
                Parameters:
                    - :logger-name: Logger name. When unspecified, uses session name (default session logger)

            - #log show [loggerFile]: Display all logs or specific log file

                Parameters:
                    - :loggerFile: Specific log file to display. Shows directory listing when unspecified

        Examples:
            - ``#log`` : List all logger statuses in current session
            - ``#log start`` : Start default session logger (using session name). Logs in plain text mode to log/name.log in append mode
            - ``#log start -r`` : Start default logger in raw mode
            - ``#log start chat`` : Start 'chat' logger for specific logging via .log() calls
            - ``#log stop`` : Stop default session logger

        Notes:
            - File mode changes (-a/-w/-n) only take effect on next logger start
            - Logging mode (-r) changes take effect immediately
        ''',

            "handle_gmcp" :
        '''
        Execution function for the embedded command #gmcp, used to manage GMCPTriggers. 
        This command can be used with no parameters, one parameter, or two parameters.
        This function should not be called directly in code.

        Usage:
            - #gmcp: Display all GMCPTriggers in this session
            - #gmcp {gmcp_key}: Show details of the GMCPTrigger named {gmcp_key} in this session
            - #gmcp {gmcp_key} {on/off/del}: Enable/disable/delete the GMCPTrigger named {gmcp_key} in this session
            - Note: GMCPTriggers can only be created through script code due to their special nature

        Parameters:
            :gmcp_key:  Name/identifier of the GMCPTrigger
            :on:       Enable
            :off:      Disable
            :del:      Delete

        Examples:
            - ``#gmcp`` : No parameters, list all GMCPTriggers in current session
            - ``#gmcp GMCP.Move`` : Single parameter, display details of GMCPTrigger named GMCP.Move
            - ``#gmcp GMCP.Move on`` : Two parameters, enable GMCPTrigger named GMCP.Move (enabled = True)
            - ``#gmcp GMCP.Move off`` : Two parameters, disable GMCPTrigger named GMCP.Move (enabled = False)
            - ``#gmcp GMCP.Move del`` : Two parameters, delete GMCPTrigger named GMCP.Move

        Related commands:
            - #alias
            - #trigger
            - #timer
        ''',

            "handle_plugins" :
        '''
        Execution function for the embedded command #plugins, displays plugin information. Can be used with no parameters or one parameter.
        This function should not be called directly in code.

        Usage:
            - #plugins: Show list of all plugins loaded in current session
            - #plugins {myplug}: Show detailed information for plugin named myplug

        Related commands:
            - #modules
        ''',

            "handle_replace" :
        '''
        Execution function for the embedded command #replace, modifies display content by replacing original line content with new message. No newline needed.
        This function should not be called directly in code.

        Usage:
            - #replace {new_display}: Replace current line display with {new_display}

        Parameters:
            - :new_display: Replacement display content (supports ANSI color codes)

        Example:
            - ``#replace %raw - Captured this line`` : Add annotation after captured line information

        Note:
            - Should be used in synchronous trigger processing. For multi-line triggers, replacement only affects last line.

        Related commands:
            - #gag
        ''',

            "handle_all" :
        '''
        Execution function for embedded command #all, sends same command to all sessions.
        This function should not be called directly in code.

        Usage:
            - #all {command}: Broadcast specified command to all sessions in current application

        Parameters:
            :command: Command to broadcast

        Example:
            - #all look: Execute 'look' command in all sessions
            - #all #cls: Clear display content for all sessions
        ''',
            "handle_save" :
        '''
        The execution function of the embedded command #save, which saves the current session variables (excluding system variables and temporary variables) to a file. This command does not take any parameters.
        System variables include %line, %copy, and %raw. Temporary variables refer to variables whose names start with an underscore.
        This function should not be called directly in the code.

        Usage:
            - #save: Save the current session variables.

        Notes:
            1. The file is saved in the current directory with the name {session_name}.mud.
            2. The Python pickle module is used to save variables, so all variables should be type introspective.
            3. Although variables support all Python types, it is still recommended to use only serializable types in variables.
            4. namedtuple is not recommended because type matching will fail after loading, and two namedtuples with the same definition will not be considered the same type.
        
        Related commands:
            - #variable
        ''',

            "handle_reset" :
        '''
        The execution function of the embedded command #reset, which resets all scripts. This command does not take any parameters.
        The reset operation will reset all triggers, commands, and incomplete tasks, and clear all triggers, commands, aliases, and variables.
        This function should not be called directly in the code.

        Usage:
            - #reset: Reset all scripts.

        Related commands:
            - #load
            - #unload
            - #reload
        ''',

            "handle_load" :
        '''
        The execution function of the embedded command #load, which performs module loading operations for the current session. When loading multiple modules, separate them with spaces or commas.
        This function should not be called directly in the code.

        Usage:
            - #load {mod1}: Load a module with the specified name.
            - #load {mod1} {mod2} ... {modn}: Load multiple modules with the specified names.
            - #load {mod1},{mod2},...{modn}: Load multiple modules with the specified names.
            - Note: When loading multiple modules, they will be loaded one by one in sequence. Therefore, if there are dependencies between modules, please pay attention to the order.
        
        Parameters:
            :modx: Module name.
    
        Examples:
            - ``#load myscript`` : Load the myscript module. First, it will look for the myscript.py file in the current directory where the PyMUD application is executed and load it.
            - ``#load pymud.pkuxkx`` : Load the pymud.pkuxkx module, which is equivalent to the import pymud.pkuxkx command in the script.
            - ``#load myscript1 myscript2`` : Load the myscript1 and myscript2 modules in sequence.
            - ``#load myscript1,myscript2`` : Multiple scripts can also be separated by commas.

        Related commands:
            - #unload
            - #reload
            - #module
        ''',

            "handle_unload" :
        '''
        The execution function of the embedded command #unload, which unloads modules.
        This function should not be called directly in the code.

        Usage:
            - #unload {modname}: Unload a loaded module with the specified name.
            - #unload {mod1} {mod2} ... {modn}: Unload multiple modules/plugins with the specified names.
            - #unload {mod1},{mod2},...{modn}: Unload multiple modules/plugins with the specified names.
            - Note: When unloading a module, the objects created by the module will not be automatically cleaned up. Instead, the unload method of the Configuration class in the module will be called. If you need to clean up the objects created by the module, please explicitly put the cleanup code in this method.
        
        Parameters:
            :modname: Module name.
            :modn: Module name.
    
        Examples:
            - ``#unload mymodule``: Unload the module named mymodule (and call the unload method of the Configuration class in it if it exists).
        
        Related commands:
            - #load
            - #reload
            - #module
        ''',
            "handle_modules" :
        '''
        The execution function of the embedded command #modules, used to manage loaded configuration modules.
        This function should not be called directly in the code.

        Usage:
            - #modules: List all loaded modules in the current session.
            - #modules <module>: Display the configuration details of the specified module.

        Parameters:
            :module: Module name (optional).
        ''',

            "handle_reload" :
        '''
        The execution function of the embedded command #reload, used to reload modules/plugins.
        This function should not be called directly in the code.

        Usage:
            - #reload: Reload all loaded modules.
            - #reload {modname}: Reload the module named modname.
            - #reload {plugins}: Reload the plugin named plugins.
            - #reload {mod1} {mod2} ... {modn}: Reload multiple modules/plugins with specified names.
            - #reload {mod1},{mod2},...{modn}: Reload multiple modules/plugins with specified names.
        
        Parameters:
            :modname: Module name.
            :plugins: Plugin name.
            :modn:    Module name.
    
        Notes:
            1. #reload can only reload modules loaded via the #load method (including those specified in pymud.cfg), but cannot reload modules imported using import xxx.
            2. If there are syntax errors in the loaded module scripts, #reload may not take effect. In this case, you need to exit and reopen PyMUD.
            3. If different modules are loaded sequentially and there are dependencies between them, when reloading, you should reload them one by one in the original dependency order; otherwise, it is easy to encounter missing dependencies or dependency errors.

        Examples:
            - ``#reload`` : Reload all loaded modules.
            - ``#reload mymodule`` : Reload the module named mymodule.
            - ``#reload myplugins`` : Reload the plugin named myplugins.
            - ``#reload mymodule myplugins`` : Reload the module named mymodule and the plugin named myplugins.

        Related commands:
            - #load
            - #unload
            - #module
        ''',

            "handle_gag" :
        '''
        The execution function of the embedded command #gag, used to prevent the current line from being displayed in the main window, usually used in triggers.
        This function should not be called directly in the code.

        Usage:
            - #gag

        Notes:
            - Once the current line is gagged, it will never be displayed again, but the corresponding trigger will still take effect.

        Related commands:
            - #replace
        ''',

            "handle_py" :
        '''
        The execution function of the embedded command #py, used to execute Python statements.
        This function should not be called directly in the code.

        Usage:
            - #py {py_code}: Execute py_code in the current context.
            - The environment is the current context, where self represents the current session.

        Examples:
            - ``#py self.info("hello")`` : Equivalent to calling ``session.info("hello")`` in the current session.
            - ``#py self.enableGroup("group1", False)`` : Equivalent to calling ``session.enableGroup("group1", False)``.
        ''',
        
            "handle_trigger" :
        '''
        The execution function of the embedded commands #trigger / #tri / #action, used to operate triggers. This command can be used with no parameters, one parameter, or two parameters.
        This function should not be called directly in the code.

        Usage:
            - #tri: Display all triggers in this session.
            - #tri {tri_id}: Display information about the trigger with id {tri_id} in this session.
            - #tri {tri_id} {on/off/del}: Enable/disable/delete the trigger with id {tri_id} in this session.
            - #tri {pattern} {code}: Create a new trigger with the matching pattern {pattern} and execute {code} when matched.
            - In the trigger's code, %line can be used to represent the line, and %1~%9 can be used to represent the captured information.

        Parameters:
            :tri_id:  The id of the Trigger.
            :on:      Enable.
            :off:     Disable.
            :del:     Delete.
            :pattern: The matching pattern of the trigger, which should be a valid Python regular expression.
            :code:    The content to be executed when the trigger is successfully matched.
    
        Examples:
            - ``#tri``: Without parameters, print and list all triggers in the current session.
            - ``#tri my_tri``: With one parameter, list detailed information about the Trigger object with id my_tri.
            - ``#tri my_tri on``: With two parameters, enable the Trigger object with id my_tri (enabled = True).
            - ``#tri my_tri off``: With two parameters, disable the Trigger object with id my_tri (enabled = False).
            - ``#tri my_tri del``: With two parameters, delete the Trigger object with id my_tri.
            - ``#tri {^[> ]*Duan Yu stumbles.+} {get duan}``: With two parameters, create a new Trigger object. Pick up Duan Yu when he is knocked down.

        Related commands:
            - #alias
            - #timer
            - #command
        ''',
                "handle_wait" :
        '''
        The execution function of the embedded commands #wait / #wa, used for asynchronous delay waiting for a specified time, which is used for delay waiting between multiple commands.
        This function should not be called directly in the code.

        Usage:
            - #wa {ms}
        
        Parameters:
            - ms: Waiting time (milliseconds)

        Example:
            - ``eat liang;#wa 300;drink jiudai``
                Eat dry food, then execute "drink from the wine bag" after a 300-millisecond delay.
        
        Related commands:
            - #gag
            - #replace
        ''',

            "handle_clear" :
        '''
        The execution function of the embedded commands #clear / #cls, used to clear the current session buffer and display.
        This function should not be called directly in the code.

        Usage:
            - #cls: Clear the current session buffer and display.
        ''',

            "handle_message" :
        '''
        The execution function of the embedded commands #message / #mess, used to pop up a dialog box to display the given information.
        This function should not be called directly in the code.

        Usage:
            - #mess {msg}: Pop up a dialog box to display the information specified by {msg}.

        Parameters:
            :msg:  The information to be displayed in the pop-up window.

        Examples:
            - ``#mess This is a test line`` : Use a pop-up window to display "This is a test line".
            - ``#mess %line`` : Use a pop-up window to display the value of the system variable %line.
        ''',

            "handle_disconnect" :
        '''
        The execution function of the embedded commands #disconnect / #dis, used to disconnect from the remote server (only effective when the remote server is already connected).
        This function should not be called directly in the code.
        
        Related commands:
            - #connect
            - #close
        ''',
        }
    },
}