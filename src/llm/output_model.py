from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, create_model


# Function to dynamically create Literal types at runtime
def create_literal_type(values):
    """
    Dynamically create a Literal type with the given values.
    This approach ensures the Literal values are visible in the JSON schema.

    Args:
        values: List or tuple of allowed values

    Returns:
        A dynamically created Literal type
    """
    # Create a dictionary of local variables for exec
    local_vars = {}

    # Generate a string representation of the Literal type
    values_str = ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in values])
    literal_code = f"from typing import Literal; LiteralType = Literal[{values_str}]"

    # Execute the code to create the Literal type
    exec(literal_code, globals(), local_vars)

    # Return the created Literal type
    return local_vars["LiteralType"]


class CommandBuilder:
    """
    A builder class for dynamically creating command validation models
    with schema-visible restricted values.
    """

    @staticmethod
    def create_argument_model(
        arg_name: str, allowed_values: Optional[List[Any]] = None
    ):
        """
        Create an argument model with properly documented allowed values

        Args:
            arg_name: Name of the argument
            allowed_values: List of allowed values, or None for unrestricted

        Returns:
            A dynamically created Pydantic model for the argument
        """
        model_name = "CommandArgument"

        if allowed_values is None:
            # Unrestricted string value
            return create_model(
                model_name,
                name=(Literal[arg_name], Field(arg_name, description="Argument name")),
                value=(str, Field(..., description="Any text value")),
            )
        else:
            # Create a Literal type with the allowed values
            value_type = create_literal_type(allowed_values)

            # Create a field with description listing allowed values
            value_desc = f"One of: {', '.join(str(v) for v in allowed_values)}"
            value_field = Field(..., description=value_desc)

            return create_model(
                model_name,
                name=(Literal[arg_name], Field(arg_name, description="Argument name")),
                value=(value_type, value_field),
            )

    @staticmethod
    def create_command_model(command_name: str, arg_specs: Dict[str, List[Any]]):
        """
        Create a command model with the specified arguments

        Args:
            command_name: Name of the command
            arg_specs: Dictionary mapping argument names to their allowed values
                      (None for unrestricted)

        Returns:
            A dynamically created Pydantic model for the command
        """
        # Create argument models for each argument
        argument_models = {
            arg_name: CommandBuilder.create_argument_model(arg_name, arg_values)
            for arg_name, arg_values in arg_specs.items()
        }

        # Handle Union of different argument types
        if len(argument_models) > 0:
            arguments_type = List[Union[tuple(argument_models.values())]]
        else:
            # Fallback if no arguments are specified
            arguments_type = List[Any]

        # Create and return the command model
        return create_model(
            "Command",
            name=(
                Literal[command_name],
                Field(command_name, description="Command name"),
            ),
            arguments=(
                arguments_type,
                Field(..., description="List of command arguments"),
            ),
        )

    @staticmethod
    def create_commands_model(command_specs: Dict[str, Dict[str, List[Any]]]):
        """
        Create a full commands model from specifications

        Args:
            command_specs: Dictionary mapping command names to their argument specifications

        Returns:
            A dynamically created Pydantic model for validating commands
        """
        # Create command models for each command type
        command_models = {
            cmd_name: CommandBuilder.create_command_model(cmd_name, arg_specs)
            for cmd_name, arg_specs in command_specs.items()
        }

        # Create the Union of all command types
        if command_models:
            commands_type = List[Union[tuple(command_models.values())]]
        else:
            commands_type = List[Any]

        # Create the main Commands model
        return create_model(
            "Commands",
            commands=(
                commands_type,
                Field(..., description="List of commands to execute"),
            ),
        )


class CommandArgument(BaseModel):
    """
    Single argument for a command execution.

    Parameters
    ----------
    name : str
        Name identifier for the argument
    value : str
        Value to be used for the argument
    """

    name: str = Field(..., description="The name of the argument")
    value: str = Field(..., description="The value of the argument")


class Command(BaseModel):
    """
    Executable command with its arguments.

    Parameters
    ----------
    name : str
        Name of the command to execute
    arguments : list[CommandArgument]
        List of arguments required for command execution
    """

    name: str = Field(..., description="The name of the command to execute")
    arguments: list[CommandArgument] = Field(
        ..., description="Arguments for the command"
    )
